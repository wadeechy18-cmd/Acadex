from tests.conftest import auth_headers, register


def register_teacher(client, email: str | None = None, school_name: str | None = None) -> dict:
    import uuid

    email = email or f"teacher.{uuid.uuid4().hex[:10]}@example.com"
    payload = {"email": email, "password": "SuperSecret123", "display_name": "Teacher", "role": "teacher"}
    if school_name:
        payload["school_name"] = school_name
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201, res.text
    body = res.json()
    return {"token": body["access_token"], "user": body["user"], "email": email}


def test_student_registration_creates_no_organizations(client):
    student = register(client, "student")
    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(student)).json()
    assert orgs == []


def test_individual_teacher_gets_personal_workspace(client):
    teacher = register_teacher(client)
    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(teacher)).json()
    assert len(orgs) == 1
    assert orgs[0]["kind"] == "personal"
    assert orgs[0]["my_role"] == "owner"


def test_school_registration_creates_personal_and_school_workspace(client):
    teacher = register_teacher(client, school_name="Springfield School")
    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(teacher)).json()
    kinds = {o["kind"] for o in orgs}
    assert kinds == {"personal", "school"}
    school = next(o for o in orgs if o["kind"] == "school")
    assert school["name"] == "Springfield School"
    assert school["my_role"] == "owner"


def test_existing_teacher_lazily_gets_personal_workspace(client, db_session):
    """Simulates a teacher account that predates this feature: no organization
    exists until they first call /organizations/me.
    """
    import uuid

    from app.models.user import TeacherProfile, User, UserRole
    from app.core.security import hash_password

    email = f"legacy.{uuid.uuid4().hex[:10]}@example.com"
    user = User(email=email, hashed_password=hash_password("SuperSecret123"), role=UserRole.TEACHER, is_active=True, is_verified=True)
    db_session.add(user)
    db_session.flush()
    db_session.add(TeacherProfile(user_id=user.id, display_name="Legacy Teacher", is_verified_teacher=False))
    db_session.commit()

    login = client.post("/api/v1/auth/login", json={"email": email, "password": "SuperSecret123"})
    token = login.json()["access_token"]

    orgs = client.get("/api/v1/organizations/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert len(orgs) == 1
    assert orgs[0]["kind"] == "personal"


def test_owner_can_add_and_remove_member(client):
    owner = register_teacher(client, school_name="Big School")
    colleague = register_teacher(client)

    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(owner)).json()
    school_id = next(o["id"] for o in orgs if o["kind"] == "school")

    add = client.post(
        f"/api/v1/organizations/{school_id}/members",
        json={"email": colleague["email"], "role": "teacher"},
        headers=auth_headers(owner),
    )
    assert add.status_code == 201, add.text
    member_id = add.json()["id"]

    # Colleague can now see the school in their own org list.
    colleague_orgs = client.get("/api/v1/organizations/me", headers=auth_headers(colleague)).json()
    assert any(o["id"] == school_id for o in colleague_orgs)

    members = client.get(f"/api/v1/organizations/{school_id}/members", headers=auth_headers(owner)).json()
    assert len(members) == 2

    remove = client.delete(f"/api/v1/organizations/{school_id}/members/{member_id}", headers=auth_headers(owner))
    assert remove.status_code == 204

    members_after = client.get(f"/api/v1/organizations/{school_id}/members", headers=auth_headers(owner)).json()
    assert len(members_after) == 1


def test_non_member_cannot_view_or_modify_school(client):
    owner = register_teacher(client, school_name="Private School")
    outsider = register_teacher(client)

    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(owner)).json()
    school_id = next(o["id"] for o in orgs if o["kind"] == "school")

    assert client.get(f"/api/v1/organizations/{school_id}/members", headers=auth_headers(outsider)).status_code == 403
    assert (
        client.post(
            f"/api/v1/organizations/{school_id}/members",
            json={"email": outsider["email"], "role": "teacher"},
            headers=auth_headers(outsider),
        ).status_code
        == 403
    )


def test_plain_teacher_member_cannot_add_members(client):
    """Being TEACHER-role within an org is not enough to manage membership --
    only OWNER/ADMIN can.
    """
    owner = register_teacher(client, school_name="Strict School")
    member = register_teacher(client)
    third_party = register_teacher(client)

    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(owner)).json()
    school_id = next(o["id"] for o in orgs if o["kind"] == "school")

    client.post(
        f"/api/v1/organizations/{school_id}/members",
        json={"email": member["email"], "role": "teacher"},
        headers=auth_headers(owner),
    )

    res = client.post(
        f"/api/v1/organizations/{school_id}/members",
        json={"email": third_party["email"], "role": "teacher"},
        headers=auth_headers(member),
    )
    assert res.status_code == 403


def test_cannot_remove_last_owner(client):
    owner = register_teacher(client, school_name="Solo School")
    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(owner)).json()
    school_id = next(o["id"] for o in orgs if o["kind"] == "school")

    members = client.get(f"/api/v1/organizations/{school_id}/members", headers=auth_headers(owner)).json()
    owner_member_id = members[0]["id"]

    res = client.delete(f"/api/v1/organizations/{school_id}/members/{owner_member_id}", headers=auth_headers(owner))
    assert res.status_code == 400


def test_personal_workspace_isolated_from_school(client):
    """A school admin must never be able to see or touch a teacher's personal
    workspace, even if that teacher is also a member of their school.
    """
    school_owner = register_teacher(client, school_name="Isolation School")
    teacher = register_teacher(client)

    school_orgs = client.get("/api/v1/organizations/me", headers=auth_headers(school_owner)).json()
    school_id = next(o["id"] for o in school_orgs if o["kind"] == "school")
    client.post(
        f"/api/v1/organizations/{school_id}/members",
        json={"email": teacher["email"], "role": "teacher"},
        headers=auth_headers(school_owner),
    )

    teacher_orgs = client.get("/api/v1/organizations/me", headers=auth_headers(teacher)).json()
    personal_id = next(o["id"] for o in teacher_orgs if o["kind"] == "personal")

    # School owner has no membership in the teacher's personal org at all.
    res = client.get(f"/api/v1/organizations/{personal_id}/members", headers=auth_headers(school_owner))
    assert res.status_code == 403
