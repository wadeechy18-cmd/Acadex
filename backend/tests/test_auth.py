from tests.conftest import auth_headers, register_school, register_teacher


def test_teacher_can_register_and_has_no_school(client):
    teacher = register_teacher(client)
    assert teacher["user"]["role"] == "teacher"

    me = client.get("/api/v1/auth/me", headers=auth_headers(teacher))
    assert me.status_code == 200
    assert me.json()["user"]["display_name"] == "Test Teacher"
    assert me.json()["school"] is None


def test_teacher_registration_rejects_duplicate_email(client):
    teacher = register_teacher(client, email="dupe@example.com")
    res = client.post(
        "/api/v1/auth/register/teacher",
        json={"email": teacher["email"], "password": "SuperSecret123", "display_name": "Another Name"},
    )
    assert res.status_code == 409


def test_school_registration_creates_school_admin_and_school(client):
    admin = register_school(client, school_name="Riverside Academy")
    assert admin["user"]["role"] == "school_admin"
    assert admin["school"]["name"] == "Riverside Academy"
    assert admin["school"]["my_role"] == "admin"


def test_login_with_correct_and_incorrect_password(client):
    teacher = register_teacher(client, email="login@example.com")
    ok = client.post("/api/v1/auth/login", json={"email": "login@example.com", "password": "SuperSecret123"})
    assert ok.status_code == 200

    bad = client.post("/api/v1/auth/login", json={"email": "login@example.com", "password": "WrongPassword1"})
    assert bad.status_code == 401


def test_login_rejects_unknown_email(client):
    res = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "SuperSecret123"})
    assert res.status_code == 401


def test_teacher_without_a_school_has_no_school_summary(client):
    teacher = register_teacher(client)
    res = client.get("/api/v1/auth/me", headers=auth_headers(teacher))
    assert res.status_code == 200
    assert res.json()["school"] is None


def test_me_reflects_school_membership_after_being_added(client):
    """Regression test: /auth/me must return the school summary too, not
    just the user -- the frontend's session-rehydration path (on a hard
    page reload) only calls /auth/me, and pages like school/teachers
    depend on the school id being present there, not only in the one-time
    login/register response.
    """
    admin = register_school(client, school_name="Rehydration School")
    teacher = register_teacher(client)
    school_id = admin["school"]["id"]

    before = client.get("/api/v1/auth/me", headers=auth_headers(teacher)).json()
    assert before["school"] is None

    client.post(f"/api/v1/schools/{school_id}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(admin))

    after = client.get("/api/v1/auth/me", headers=auth_headers(teacher)).json()
    assert after["school"]["id"] == school_id
    assert after["school"]["my_role"] == "teacher"


def test_forgot_password_and_reset_flow(client):
    teacher = register_teacher(client, email="reset@example.com")

    forgot = client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
    assert forgot.status_code == 200
    token = forgot.json()["reset_token"]
    assert token  # dev/test environment surfaces it since there's no email backend

    reset = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "BrandNewPassword1"})
    assert reset.status_code == 204

    old_login = client.post("/api/v1/auth/login", json={"email": "reset@example.com", "password": "SuperSecret123"})
    assert old_login.status_code == 401
    new_login = client.post("/api/v1/auth/login", json={"email": "reset@example.com", "password": "BrandNewPassword1"})
    assert new_login.status_code == 200


def test_forgot_password_for_unknown_email_gives_the_same_generic_response(client):
    res = client.post("/api/v1/auth/forgot-password", json={"email": "ghost@example.com"})
    assert res.status_code == 200
    assert res.json()["reset_token"] is None


def test_reset_password_rejects_a_reused_or_invalid_token(client):
    res = client.post("/api/v1/auth/reset-password", json={"token": "not-a-real-token", "new_password": "SomethingElse1"})
    assert res.status_code == 400


def test_unauthenticated_request_to_me_is_rejected(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
