from tests.conftest import auth_headers
from tests.test_lesson_plans import create_lesson_plan, create_school_class
from tests.test_organizations import register_teacher
from tests.test_resources import upload
from tests.test_worksheets import create_homework, create_worksheet

_A_MONDAY = "2026-09-14"


def add_colleague(client, owner, org_id, role="teacher"):
    colleague = register_teacher(client)
    res = client.post(
        f"/api/v1/organizations/{org_id}/members", json={"email": colleague["email"], "role": role}, headers=auth_headers(owner)
    )
    assert res.status_code == 201, res.text
    return colleague


# --- Curriculum subjects ---


def test_admin_can_create_and_list_curriculum_subjects(client):
    owner, org_id, _ = create_school_class(client)
    res = client.post(
        f"/api/v1/organizations/{org_id}/curriculum-subjects",
        json={"name": "Mathematics", "key_stage": "KS2"},
        headers=auth_headers(owner),
    )
    assert res.status_code == 201, res.text

    listed = client.get(f"/api/v1/organizations/{org_id}/curriculum-subjects", headers=auth_headers(owner)).json()
    assert [s["name"] for s in listed] == ["Mathematics"]


def test_plain_teacher_can_view_but_not_create_curriculum_subjects(client):
    owner, org_id, _ = create_school_class(client)
    teacher = add_colleague(client, owner, org_id, role="teacher")

    view = client.get(f"/api/v1/organizations/{org_id}/curriculum-subjects", headers=auth_headers(teacher))
    assert view.status_code == 200

    create = client.post(
        f"/api/v1/organizations/{org_id}/curriculum-subjects", json={"name": "Science"}, headers=auth_headers(teacher)
    )
    assert create.status_code == 403


def test_duplicate_curriculum_subject_name_is_rejected(client):
    owner, org_id, _ = create_school_class(client)
    client.post(f"/api/v1/organizations/{org_id}/curriculum-subjects", json={"name": "English"}, headers=auth_headers(owner))
    dup = client.post(f"/api/v1/organizations/{org_id}/curriculum-subjects", json={"name": "English"}, headers=auth_headers(owner))
    assert dup.status_code == 409


def test_admin_can_delete_curriculum_subject(client):
    owner, org_id, _ = create_school_class(client)
    created = client.post(
        f"/api/v1/organizations/{org_id}/curriculum-subjects", json={"name": "Art"}, headers=auth_headers(owner)
    ).json()

    res = client.delete(f"/api/v1/organizations/{org_id}/curriculum-subjects/{created['id']}", headers=auth_headers(owner))
    assert res.status_code == 204
    assert client.get(f"/api/v1/organizations/{org_id}/curriculum-subjects", headers=auth_headers(owner)).json() == []


# --- Activity feed ---


def test_creating_a_class_and_lesson_plan_appears_in_activity(client):
    owner, org_id, class_id = create_school_class(client)
    create_lesson_plan(client, owner, class_id)

    activity = client.get(f"/api/v1/organizations/{org_id}/activity", headers=auth_headers(owner)).json()
    actions = [a["action"] for a in activity]
    assert "class.created" in actions
    assert "lesson_plan.created" in actions


def test_resource_upload_and_worksheet_homework_creation_appear_in_activity(client):
    owner, org_id, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)
    upload(client, owner, org_id, b"some scheme of work text", "scheme.txt", "text/plain")
    create_worksheet(client, owner, plan["id"])
    create_homework(client, owner, plan["id"])

    activity = client.get(f"/api/v1/organizations/{org_id}/activity", headers=auth_headers(owner)).json()
    actions = {a["action"] for a in activity}
    assert actions == {"class.created", "lesson_plan.created", "resource.uploaded", "worksheet.created", "homework.created"}


def test_activity_feed_is_admin_only(client):
    owner, org_id, _ = create_school_class(client)
    teacher = add_colleague(client, owner, org_id, role="teacher")

    res = client.get(f"/api/v1/organizations/{org_id}/activity", headers=auth_headers(teacher))
    assert res.status_code == 403


def test_activity_feed_is_scoped_to_its_own_organization(client):
    owner_a, org_a, class_a = create_school_class(client)
    create_lesson_plan(client, owner_a, class_a)

    owner_b, org_b, _ = create_school_class(client)

    # org_b has its own class.created entry from create_school_class's setup,
    # but must never see org_a's lesson_plan.created (or org_a's class at all).
    activity_b = client.get(f"/api/v1/organizations/{org_b}/activity", headers=auth_headers(owner_b)).json()
    assert "lesson_plan.created" not in {a["action"] for a in activity_b}
    assert all(a["target_id"] != class_a for a in activity_b)


# --- Teacher overview ---


def test_teacher_overview_reports_class_and_lesson_plan_counts(client):
    owner, org_id, class_id = create_school_class(client)
    create_lesson_plan(client, owner, class_id)
    create_lesson_plan(client, owner, class_id, title="Second plan", topic="Second topic")
    teacher = add_colleague(client, owner, org_id, role="teacher")

    overview = client.get(f"/api/v1/organizations/{org_id}/teacher-overview", headers=auth_headers(owner)).json()
    by_user = {row["email"]: row for row in overview}
    assert by_user[owner["email"]]["class_count"] == 1
    assert by_user[owner["email"]]["lesson_plan_count"] == 2
    assert by_user[teacher["email"]]["class_count"] == 0


def test_teacher_overview_is_admin_only(client):
    owner, org_id, _ = create_school_class(client)
    teacher = add_colleague(client, owner, org_id, role="teacher")

    res = client.get(f"/api/v1/organizations/{org_id}/teacher-overview", headers=auth_headers(teacher))
    assert res.status_code == 403


# --- Weekly overview (admin read-only into a teacher's own timetable) ---


def test_admin_can_view_a_teachers_weekly_plan_read_only(client):
    owner, org_id, class_id = create_school_class(client)
    teacher = add_colleague(client, owner, org_id, role="teacher")

    plan = client.post(
        f"/api/v1/organizations/{org_id}/weekly-plans", json={"week_start_date": _A_MONDAY}, headers=auth_headers(teacher)
    ).json()
    teacher_class = client.post(
        f"/api/v1/organizations/{org_id}/classes",
        json={"name": "Teacher's Own Class", "subject_name": "Art", "year_group": "year_5"},
        headers=auth_headers(teacher),
    ).json()
    client.post(
        f"/api/v1/weekly-plans/{plan['id']}/items",
        json={"class_id": teacher_class["id"], "day_of_week": "monday", "start_time": "09:00:00", "duration_minutes": 50, "topic_override": "Painting"},
        headers=auth_headers(teacher),
    )

    overview = client.get(
        f"/api/v1/organizations/{org_id}/weekly-overview",
        params={"teacher_user_id": teacher["user"]["id"], "week_start_date": _A_MONDAY},
        headers=auth_headers(owner),
    )
    assert overview.status_code == 200, overview.text
    assert overview.json()["items"][0]["topic"] == "Painting"


def test_plain_teacher_cannot_use_weekly_overview_on_a_colleague(client):
    owner, org_id, _ = create_school_class(client)
    teacher_a = add_colleague(client, owner, org_id, role="teacher")
    teacher_b = add_colleague(client, owner, org_id, role="teacher")
    client.post(
        f"/api/v1/organizations/{org_id}/weekly-plans", json={"week_start_date": _A_MONDAY}, headers=auth_headers(teacher_a)
    )

    res = client.get(
        f"/api/v1/organizations/{org_id}/weekly-overview",
        params={"teacher_user_id": teacher_a["user"]["id"], "week_start_date": _A_MONDAY},
        headers=auth_headers(teacher_b),
    )
    assert res.status_code == 403


def test_weekly_overview_404s_when_teacher_has_no_plan_for_that_week(client):
    owner, org_id, _ = create_school_class(client)
    teacher = add_colleague(client, owner, org_id, role="teacher")

    res = client.get(
        f"/api/v1/organizations/{org_id}/weekly-overview",
        params={"teacher_user_id": teacher["user"]["id"], "week_start_date": _A_MONDAY},
        headers=auth_headers(owner),
    )
    assert res.status_code == 404
