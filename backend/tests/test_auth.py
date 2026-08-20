from tests.conftest import auth_headers, register


def test_register_and_login(client):
    account = register(client, "student")
    res = client.post("/api/v1/auth/login", json={"email": account["email"], "password": "SuperSecret123"})
    assert res.status_code == 200
    assert res.json()["user"]["role"] == "student"


def test_duplicate_email_rejected(client):
    account = register(client, "student")
    res = client.post(
        "/api/v1/auth/register",
        json={"email": account["email"], "password": "SuperSecret123", "display_name": "X", "role": "student"},
    )
    assert res.status_code == 409


def test_wrong_password_rejected(client):
    account = register(client, "student")
    res = client.post("/api/v1/auth/login", json={"email": account["email"], "password": "WrongPassword1"})
    assert res.status_code == 401


def test_admin_cannot_self_register(client):
    res = client.post(
        "/api/v1/auth/register",
        json={"email": "fake-admin@example.com", "password": "SuperSecret123", "display_name": "X", "role": "admin"},
    )
    assert res.status_code == 422


def test_me_requires_authentication(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_returns_current_user(client):
    account = register(client, "teacher")
    res = client.get("/api/v1/auth/me", headers=auth_headers(account))
    assert res.status_code == 200
    assert res.json()["email"] == account["email"]


def test_password_reset_invalidated_by_password_change(client):
    account = register(client, "student")

    req = client.post("/api/v1/auth/password-reset/request", json={"email": account["email"]})
    token = req.json()["dev_reset_token"]

    confirm = client.post("/api/v1/auth/password-reset/confirm", json={"token": token, "new_password": "BrandNewPass456"})
    assert confirm.status_code == 204

    old_login = client.post("/api/v1/auth/login", json={"email": account["email"], "password": "SuperSecret123"})
    assert old_login.status_code == 401

    new_login = client.post("/api/v1/auth/login", json={"email": account["email"], "password": "BrandNewPass456"})
    assert new_login.status_code == 200

    # The same token should not be reusable now that the password hash changed.
    replay = client.post("/api/v1/auth/password-reset/confirm", json={"token": token, "new_password": "AnotherPass789"})
    assert replay.status_code == 400


def test_password_reset_request_does_not_leak_account_existence(client):
    res = client.post("/api/v1/auth/password-reset/request", json={"email": "nobody@example.com"})
    assert res.status_code == 202
    assert "dev_reset_token" not in res.json()
