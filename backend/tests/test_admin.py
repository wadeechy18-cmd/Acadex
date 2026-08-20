from tests.conftest import auth_headers, register
from tests.test_education import assign_teacher_to_subject, make_admin


def test_stats_requires_admin(client):
    student = register(client, "student")
    assert client.get("/api/v1/admin/stats", headers=auth_headers(student)).status_code == 403


def test_stats_counts_reflect_data(client, db_session):
    admin_headers = make_admin(client, db_session)
    register(client, "student")
    register(client, "student")

    stats = client.get("/api/v1/admin/stats", headers=admin_headers).json()
    assert stats["total_students"] >= 2
    assert stats["total_admins"] >= 1


def test_admin_cannot_deactivate_self(client, db_session):
    admin_headers = make_admin(client, db_session)
    me = client.get("/api/v1/auth/me", headers=admin_headers).json()

    res = client.patch(f"/api/v1/admin/users/{me['id']}/active", json={"is_active": False}, headers=admin_headers)
    assert res.status_code == 400


def test_deactivated_user_cannot_log_in(client, db_session):
    admin_headers = make_admin(client, db_session)
    student = register(client, "student")

    client.patch(f"/api/v1/admin/users/{student['user']['id']}/active", json={"is_active": False}, headers=admin_headers)

    login = client.post("/api/v1/auth/login", json={"email": student["email"], "password": "SuperSecret123"})
    assert login.status_code == 403


def test_teacher_verify_and_subject_assignment(client, db_session, subject):
    admin_headers = make_admin(client, db_session)
    teacher = register(client, "teacher")

    teachers = client.get("/api/v1/admin/teachers", headers=admin_headers).json()
    profile = next(t for t in teachers if t["user_id"] == teacher["user"]["id"])
    assert profile["is_verified_teacher"] is False

    verify = client.patch(f"/api/v1/admin/teachers/{profile['id']}/verify", json={"is_verified_teacher": True}, headers=admin_headers)
    assert verify.json()["is_verified_teacher"] is True

    assign = client.post(f"/api/v1/admin/teachers/{profile['id']}/subjects", json={"subject_id": str(subject.id)}, headers=admin_headers)
    assert assign.status_code == 201

    updated = client.get("/api/v1/admin/teachers", headers=admin_headers).json()
    updated_profile = next(t for t in updated if t["id"] == profile["id"])
    assert any(s["id"] == str(subject.id) for s in updated_profile["subjects"])

    # And that assignment is what actually lets the teacher manage the subject.
    res = client.post(
        "/api/v1/courses",
        json={"subject_id": str(subject.id), "title": "Now allowed", "slug": "now-allowed-slug"},
        headers=auth_headers(teacher),
    )
    assert res.status_code == 201


def test_unverified_teacher_can_still_manage_assigned_subject(client, db_session, subject):
    """Verification is a trust badge shown to students, not a permission gate —
    subject assignment alone is what the ownership check requires.
    """
    teacher = register(client, "teacher")
    assign_teacher_to_subject(db_session, teacher["email"], subject.id)

    res = client.post(
        "/api/v1/courses",
        json={"subject_id": str(subject.id), "title": "Unverified but assigned", "slug": "unverified-assigned-slug"},
        headers=auth_headers(teacher),
    )
    assert res.status_code == 201
