from tests.conftest import auth_headers, register_school, register_teacher


def test_admin_can_add_and_remove_a_teacher(client):
    admin = register_school(client, school_name="Add/Remove School")
    teacher = register_teacher(client)
    school_id = admin["school"]["id"]

    add = client.post(f"/api/v1/schools/{school_id}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(admin))
    assert add.status_code == 201, add.text
    member_id = add.json()["id"]

    members = client.get(f"/api/v1/schools/{school_id}/members", headers=auth_headers(admin)).json()
    assert len(members) == 2

    remove = client.delete(f"/api/v1/schools/{school_id}/members/{member_id}", headers=auth_headers(admin))
    assert remove.status_code == 204
    assert len(client.get(f"/api/v1/schools/{school_id}/members", headers=auth_headers(admin)).json()) == 1


def test_added_teacher_can_see_the_school_in_their_own_profile(client):
    admin = register_school(client, school_name="Visibility School")
    teacher = register_teacher(client)
    school_id = admin["school"]["id"]

    client.post(f"/api/v1/schools/{school_id}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(admin))

    me = client.get("/api/v1/auth/me", headers=auth_headers(teacher)).json()
    assert me["user"]["role"] == "teacher"
    # Login again to get a fresh school summary (registered before membership existed).
    relogin = client.post("/api/v1/auth/login", json={"email": teacher["email"], "password": "SuperSecret123"})
    assert relogin.json()["school"]["id"] == school_id
    assert relogin.json()["school"]["my_role"] == "teacher"


def test_cannot_add_teacher_with_unknown_email(client):
    admin = register_school(client, school_name="Unknown Email School")
    res = client.post(
        f"/api/v1/schools/{admin['school']['id']}/members",
        json={"email": "nobody@example.com", "role": "teacher"},
        headers=auth_headers(admin),
    )
    assert res.status_code == 404


def test_cannot_add_a_teacher_already_at_another_school(client):
    admin_a = register_school(client, school_name="School A")
    admin_b = register_school(client, school_name="School B")
    teacher = register_teacher(client)

    first = client.post(
        f"/api/v1/schools/{admin_a['school']['id']}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(admin_a)
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/schools/{admin_b['school']['id']}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(admin_b)
    )
    assert second.status_code == 409


def test_non_member_cannot_view_or_modify_a_school(client):
    admin = register_school(client, school_name="Private School")
    outsider = register_teacher(client)
    school_id = admin["school"]["id"]

    assert client.get(f"/api/v1/schools/{school_id}/members", headers=auth_headers(outsider)).status_code == 403
    assert (
        client.post(
            f"/api/v1/schools/{school_id}/members", json={"email": outsider["email"], "role": "teacher"}, headers=auth_headers(outsider)
        ).status_code
        == 403
    )


def test_plain_teacher_member_cannot_add_members(client):
    """Being a TEACHER-role member isn't enough to manage school membership --
    only an ADMIN-role member can.
    """
    admin = register_school(client, school_name="Strict School")
    member = register_teacher(client)
    third_party = register_teacher(client)
    school_id = admin["school"]["id"]

    client.post(f"/api/v1/schools/{school_id}/members", json={"email": member["email"], "role": "teacher"}, headers=auth_headers(admin))

    res = client.post(
        f"/api/v1/schools/{school_id}/members", json={"email": third_party["email"], "role": "teacher"}, headers=auth_headers(member)
    )
    assert res.status_code == 403


def test_cannot_remove_the_last_admin(client):
    admin = register_school(client, school_name="Solo Admin School")
    school_id = admin["school"]["id"]

    members = client.get(f"/api/v1/schools/{school_id}/members", headers=auth_headers(admin)).json()
    admin_member_id = members[0]["id"]

    res = client.delete(f"/api/v1/schools/{school_id}/members/{admin_member_id}", headers=auth_headers(admin))
    assert res.status_code == 400


def test_two_schools_are_fully_isolated_from_each_other(client):
    admin_a = register_school(client, school_name="Isolated School A")
    admin_b = register_school(client, school_name="Isolated School B")

    res = client.get(f"/api/v1/schools/{admin_a['school']['id']}/members", headers=auth_headers(admin_b))
    assert res.status_code == 403
