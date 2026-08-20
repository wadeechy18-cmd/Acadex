from tests.conftest import auth_headers, register


def test_enroll_and_dashboard_reflects_progress(client, published_course):
    student = register(client, "student")
    topic = published_course.chapters[0].topics[0]

    enroll = client.post("/api/v1/enrollments", json={"course_id": str(published_course.id)}, headers=auth_headers(student))
    assert enroll.status_code == 201

    # Re-enrolling is idempotent, not an error.
    enroll_again = client.post("/api/v1/enrollments", json={"course_id": str(published_course.id)}, headers=auth_headers(student))
    assert enroll_again.status_code == 201

    progress = client.put(
        f"/api/v1/progress/{topic.id}", json={"completion_percentage": 50, "last_position_seconds": 30}, headers=auth_headers(student)
    )
    assert progress.status_code == 200
    assert progress.json()["completed_at"] is None

    dashboard = client.get("/api/v1/dashboard/me", headers=auth_headers(student)).json()
    assert dashboard["my_courses"][0]["completion_percentage"] == 50.0
    assert dashboard["continue_learning"]["completion_percentage"] == 50.0


def test_progress_completed_at_set_at_100_and_cleared_below(client, published_course):
    student = register(client, "student")
    topic = published_course.chapters[0].topics[0]

    full = client.put(f"/api/v1/progress/{topic.id}", json={"completion_percentage": 100}, headers=auth_headers(student))
    assert full.json()["completed_at"] is not None

    partial = client.put(f"/api/v1/progress/{topic.id}", json={"completion_percentage": 80}, headers=auth_headers(student))
    assert partial.json()["completed_at"] is None


def test_cannot_enroll_in_unpublished_course(client, db_session, subject):
    from app.models.education import Course

    draft = Course(subject_id=subject.id, title="Draft", slug="draft-slug-unpub", is_published=False)
    db_session.add(draft)
    db_session.commit()

    student = register(client, "student")
    res = client.post("/api/v1/enrollments", json={"course_id": str(draft.id)}, headers=auth_headers(student))
    assert res.status_code == 404


def test_bookmark_create_list_delete(client, published_course):
    student = register(client, "student")
    lesson = published_course.chapters[0].topics[0].lessons[0]

    created = client.post(
        "/api/v1/bookmarks", json={"target_type": "lesson", "target_id": str(lesson.id)}, headers=auth_headers(student)
    )
    assert created.status_code == 201
    bookmark_id = created.json()["id"]

    listed = client.get("/api/v1/bookmarks/me", headers=auth_headers(student))
    assert len(listed.json()) == 1

    deleted = client.delete(f"/api/v1/bookmarks/{bookmark_id}", headers=auth_headers(student))
    assert deleted.status_code == 204
    assert client.get("/api/v1/bookmarks/me", headers=auth_headers(student)).json() == []


def test_student_cannot_see_another_students_dashboard_data(client, published_course):
    student_a = register(client, "student")
    student_b = register(client, "student")

    client.post("/api/v1/enrollments", json={"course_id": str(published_course.id)}, headers=auth_headers(student_a))

    dashboard_b = client.get("/api/v1/dashboard/me", headers=auth_headers(student_b)).json()
    assert dashboard_b["my_courses"] == []
