import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.limiter import limiter
from app.db.base_all import Base
from app.db.session import get_db
from app.main import app

TEST_DATABASE_URL = get_settings().database_url.rsplit("/", 1)[0] + "/acadex_test"

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    """Wraps each test in an outer transaction + a SAVEPOINT. Application code
    calling session.commit() only ends the SAVEPOINT (a new one is immediately
    restarted); the outer transaction is rolled back at teardown, so nothing a
    test does — including through the app's normal commit() calls — persists
    to the next test.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """The rate limiter (see app.core.limiter) tracks requests per client IP in
    process-global memory. TestClient always presents the same fake IP, so
    without a reset, tests that each register a couple of users quickly trip
    the real /auth/register limit and fail on request count, not on behavior.
    """
    limiter.reset()
    yield


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def register_teacher(client: TestClient, email: str | None = None, display_name: str = "Test Teacher") -> dict:
    import uuid

    email = email or f"teacher.{uuid.uuid4().hex[:10]}@example.com"
    res = client.post(
        "/api/v1/auth/register/teacher",
        json={"email": email, "password": "SuperSecret123", "display_name": display_name},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    return {"token": body["access_token"], "user": body["user"], "email": email}


def register_school(
    client: TestClient, school_name: str = "Test School", admin_email: str | None = None
) -> dict:
    import uuid

    admin_email = admin_email or f"admin.{uuid.uuid4().hex[:10]}@example.com"
    res = client.post(
        "/api/v1/auth/register/school",
        json={
            "school_name": school_name,
            "admin_email": admin_email,
            "admin_password": "SuperSecret123",
            "admin_display_name": "Test Admin",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    return {"token": body["access_token"], "user": body["user"], "school": body["school"], "email": admin_email}


def auth_headers(account: dict) -> dict:
    return {"Authorization": f"Bearer {account['token']}"}
