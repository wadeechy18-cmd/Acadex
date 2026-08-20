from app.core.security import hash_password
from app.models.user import AdminProfile, TeacherProfile, TeacherSubject, User, UserRole
from tests.conftest import auth_headers, register


def make_admin(client, db_session) -> dict:
    """Admins can't self-register, so create one directly in the database —
    the same shape scripts/create_admin.py produces — then log in normally.
    """
    email = "admin.test@example.com"
    user = User(
        email=email, hashed_password=hash_password("SuperSecret123"), role=UserRole.ADMIN, is_active=True, is_verified=True
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(AdminProfile(user_id=user.id, display_name="Test Admin"))
    db_session.commit()

    res = client.post("/api/v1/auth/login", json={"email": email, "password": "SuperSecret123"})
    assert res.status_code == 200, res.text
    return auth_headers({"token": res.json()["access_token"]})


def assign_teacher_to_subject(db_session, teacher_email: str, subject_id) -> None:
    user = db_session.query(User).filter_by(email=teacher_email).first()
    profile = db_session.query(TeacherProfile).filter_by(user_id=user.id).first()
    db_session.add(TeacherSubject(teacher_profile_id=profile.id, subject_id=subject_id))
    db_session.commit()


def test_student_cannot_create_subject(client, subject):
    student = register(client, "student")
    res = client.post(
        "/api/v1/subjects",
        json={"name": "X", "slug": "x-subject", "education_level_id": str(subject.education_level_id)},
        headers=auth_headers(student),
    )
    assert res.status_code == 403


def test_teacher_cannot_create_subject(client, subject):
    teacher = register(client, "teacher")
    res = client.post(
        "/api/v1/subjects",
        json={"name": "X", "slug": "x-subject", "education_level_id": str(subject.education_level_id)},
        headers=auth_headers(teacher),
    )
    assert res.status_code == 403


def test_unassigned_teacher_cannot_create_course(client, subject):
    teacher = register(client, "teacher")
    res = client.post(
        "/api/v1/courses",
        json={"subject_id": str(subject.id), "title": "Course", "slug": "course-slug"},
        headers=auth_headers(teacher),
    )
    assert res.status_code == 403


def test_assigned_teacher_can_create_course(client, db_session, subject):
    teacher = register(client, "teacher")
    assign_teacher_to_subject(db_session, teacher["email"], subject.id)

    res = client.post(
        "/api/v1/courses",
        json={"subject_id": str(subject.id), "title": "Course", "slug": "assigned-course-slug"},
        headers=auth_headers(teacher),
    )
    assert res.status_code == 201
    assert res.json()["is_published"] is False


def test_admin_can_create_course_in_any_subject(client, db_session, subject):
    admin_headers = make_admin(client, db_session)
    res = client.post(
        "/api/v1/courses",
        json={"subject_id": str(subject.id), "title": "Admin Course", "slug": "admin-course-slug"},
        headers=admin_headers,
    )
    assert res.status_code == 201


def test_duplicate_slug_rejected(client, db_session, subject):
    admin_headers = make_admin(client, db_session)
    payload = {"subject_id": str(subject.id), "title": "Course", "slug": "dup-slug"}
    first = client.post("/api/v1/courses", json=payload, headers=admin_headers)
    assert first.status_code == 201
    second = client.post("/api/v1/courses", json={**payload, "title": "Other"}, headers=admin_headers)
    assert second.status_code == 409


def test_unpublished_course_hidden_from_students(client, db_session, subject):
    admin_headers = make_admin(client, db_session)
    course = client.post(
        "/api/v1/courses",
        json={"subject_id": str(subject.id), "title": "Draft Course", "slug": "draft-course-slug"},
        headers=admin_headers,
    ).json()

    student = register(client, "student")
    res = client.get(f"/api/v1/courses/{course['slug']}", headers=auth_headers(student))
    assert res.status_code == 404

    res_as_admin = client.get(f"/api/v1/courses/{course['slug']}", headers=admin_headers)
    assert res_as_admin.status_code == 200
