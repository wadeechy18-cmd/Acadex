from datetime import date, timedelta

from tests.conftest import auth_headers, register_school, register_teacher


def _school_with_teacher(client):
    admin = register_school(client, school_name="Task School")
    teacher = register_teacher(client)
    school_id = admin["school"]["id"]
    client.post(
        f"/api/v1/schools/{school_id}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(admin)
    )
    return admin, teacher, school_id


def test_admin_can_create_list_update_and_delete_a_task(client):
    admin, teacher, school_id = _school_with_teacher(client)
    deadline = str(date.today() + timedelta(days=7))

    create = client.post(
        f"/api/v1/schools/{school_id}/tasks",
        json={"title": "Mark books", "assigned_to_user_id": teacher["user"]["id"], "deadline": deadline, "priority": "high"},
        headers=auth_headers(admin),
    )
    assert create.status_code == 201, create.text
    task = create.json()
    assert task["status"] == "pending"
    assert task["effective_status"] == "pending"
    assert task["assigned_to_name"] == "Test Teacher"

    listing = client.get(f"/api/v1/schools/{school_id}/tasks", headers=auth_headers(admin))
    assert len(listing.json()) == 1

    update = client.patch(
        f"/api/v1/schools/{school_id}/tasks/{task['id']}",
        json={
            "title": "Mark books (updated)",
            "assigned_to_user_id": teacher["user"]["id"],
            "deadline": deadline,
            "priority": "medium",
            "status": "in_progress",
        },
        headers=auth_headers(admin),
    )
    assert update.status_code == 200
    assert update.json()["status"] == "in_progress"

    delete = client.delete(f"/api/v1/schools/{school_id}/tasks/{task['id']}", headers=auth_headers(admin))
    assert delete.status_code == 204


def test_task_past_its_deadline_shows_as_overdue_unless_completed(client):
    admin, teacher, school_id = _school_with_teacher(client)
    past_deadline = str(date.today() - timedelta(days=3))

    create = client.post(
        f"/api/v1/schools/{school_id}/tasks",
        json={"title": "Overdue task", "assigned_to_user_id": teacher["user"]["id"], "deadline": past_deadline},
        headers=auth_headers(admin),
    )
    task = create.json()
    assert task["status"] == "pending"
    assert task["effective_status"] == "overdue"

    complete = client.patch(
        f"/api/v1/schools/{school_id}/tasks/{task['id']}",
        json={
            "title": task["title"],
            "assigned_to_user_id": teacher["user"]["id"],
            "deadline": past_deadline,
            "priority": "medium",
            "status": "completed",
        },
        headers=auth_headers(admin),
    )
    assert complete.json()["effective_status"] == "completed"


def test_a_teacher_can_view_and_update_status_of_their_own_tasks(client):
    admin, teacher, school_id = _school_with_teacher(client)
    deadline = str(date.today() + timedelta(days=1))
    create = client.post(
        f"/api/v1/schools/{school_id}/tasks",
        json={"title": "Prepare handout", "assigned_to_user_id": teacher["user"]["id"], "deadline": deadline},
        headers=auth_headers(admin),
    )
    task_id = create.json()["id"]

    mine = client.get("/api/v1/tasks/mine", headers=auth_headers(teacher))
    assert mine.status_code == 200
    assert len(mine.json()) == 1

    update = client.patch(f"/api/v1/tasks/{task_id}/status", json={"status": "in_progress"}, headers=auth_headers(teacher))
    assert update.status_code == 200
    assert update.json()["status"] == "in_progress"


def test_plain_teacher_member_cannot_create_a_task(client):
    admin, teacher, school_id = _school_with_teacher(client)
    deadline = str(date.today() + timedelta(days=1))
    res = client.post(
        f"/api/v1/schools/{school_id}/tasks",
        json={"title": "Not allowed", "assigned_to_user_id": teacher["user"]["id"], "deadline": deadline},
        headers=auth_headers(teacher),
    )
    assert res.status_code == 403


def test_cannot_assign_a_task_to_someone_outside_the_school(client):
    admin, teacher, school_id = _school_with_teacher(client)
    outsider = register_teacher(client)
    deadline = str(date.today() + timedelta(days=1))

    res = client.post(
        f"/api/v1/schools/{school_id}/tasks",
        json={"title": "Bad assignment", "assigned_to_user_id": outsider["user"]["id"], "deadline": deadline},
        headers=auth_headers(admin),
    )
    assert res.status_code == 400


def test_a_teacher_cannot_see_or_update_status_of_someone_elses_task(client):
    admin, teacher, school_id = _school_with_teacher(client)
    other_teacher = register_teacher(client)
    deadline = str(date.today() + timedelta(days=1))
    create = client.post(
        f"/api/v1/schools/{school_id}/tasks",
        json={"title": "Only for teacher", "assigned_to_user_id": teacher["user"]["id"], "deadline": deadline},
        headers=auth_headers(admin),
    )
    task_id = create.json()["id"]

    assert client.get("/api/v1/tasks/mine", headers=auth_headers(other_teacher)).json() == []
    res = client.patch(f"/api/v1/tasks/{task_id}/status", json={"status": "completed"}, headers=auth_headers(other_teacher))
    assert res.status_code == 404


def test_tasks_are_isolated_between_schools(client):
    admin_a, teacher_a, school_a = _school_with_teacher(client)
    admin_b = register_school(client, school_name="Other Task School")

    res = client.get(f"/api/v1/schools/{school_a}/tasks", headers=auth_headers(admin_b))
    assert res.status_code == 403
