from tests.conftest import auth_headers, register_school, register_teacher


def test_admin_actions_are_recorded_in_the_audit_log(client):
    admin = register_school(client, school_name="Audit School")
    teacher = register_teacher(client)
    school_id = admin["school"]["id"]

    client.post(f"/api/v1/schools/{school_id}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(admin))

    log = client.get(f"/api/v1/schools/{school_id}/audit-log", headers=auth_headers(admin))
    assert log.status_code == 200
    actions = [entry["action"] for entry in log.json()]
    assert "member.add" in actions
    entry = next(e for e in log.json() if e["action"] == "member.add")
    assert entry["actor_name"] == "Test Admin"
    assert entry["details"]["email"] == teacher["email"]


def test_removing_a_member_is_also_logged(client):
    admin = register_school(client, school_name="Audit School 2")
    teacher = register_teacher(client)
    school_id = admin["school"]["id"]
    add = client.post(
        f"/api/v1/schools/{school_id}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(admin)
    ).json()

    client.delete(f"/api/v1/schools/{school_id}/members/{add['id']}", headers=auth_headers(admin))

    log = client.get(f"/api/v1/schools/{school_id}/audit-log", headers=auth_headers(admin)).json()
    assert any(e["action"] == "member.remove" for e in log)


def test_plain_teacher_cannot_view_the_audit_log(client):
    admin = register_school(client, school_name="Audit School 3")
    teacher = register_teacher(client)
    school_id = admin["school"]["id"]
    client.post(f"/api/v1/schools/{school_id}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(admin))

    res = client.get(f"/api/v1/schools/{school_id}/audit-log", headers=auth_headers(teacher))
    assert res.status_code == 403


def test_audit_log_is_isolated_between_schools(client):
    admin_a = register_school(client, school_name="Audit School A")
    admin_b = register_school(client, school_name="Audit School B")

    res = client.get(f"/api/v1/schools/{admin_a['school']['id']}/audit-log", headers=auth_headers(admin_b))
    assert res.status_code == 403
