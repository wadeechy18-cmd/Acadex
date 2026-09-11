from datetime import date

from tests.conftest import auth_headers
from tests.test_lesson_plans import create_lesson_plan, create_school_class
from tests.test_organizations import register_teacher

# A Wednesday -- deliberately not a Monday, to prove normalisation works.
_A_WEDNESDAY = "2026-09-16"
_THAT_WEEKS_MONDAY = "2026-09-14"


def create_weekly_plan(client, owner, org_id, week_start_date=_A_WEDNESDAY):
    res = client.post(
        f"/api/v1/organizations/{org_id}/weekly-plans", json={"week_start_date": week_start_date}, headers=auth_headers(owner)
    )
    assert res.status_code == 201, res.text
    return res.json()


def test_can_create_weekly_plans_for_the_same_week_in_two_different_organizations(client):
    """Regression test: every teacher has a PERSONAL org plus can belong to a
    SCHOOL org, and needs an independent weekly plan in each for the same
    calendar week -- the uniqueness constraint must be scoped per
    organization, not just per teacher+week.
    """
    from tests.test_organizations import register_teacher as _register_teacher

    owner = _register_teacher(client, school_name="Two-Org School")
    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(owner)).json()
    personal_id = next(o["id"] for o in orgs if o["kind"] == "personal")
    school_id = next(o["id"] for o in orgs if o["kind"] == "school")

    personal_plan = client.post(
        f"/api/v1/organizations/{personal_id}/weekly-plans", json={"week_start_date": _A_WEDNESDAY}, headers=auth_headers(owner)
    )
    school_plan = client.post(
        f"/api/v1/organizations/{school_id}/weekly-plans", json={"week_start_date": _A_WEDNESDAY}, headers=auth_headers(owner)
    )
    assert personal_plan.status_code == 201, personal_plan.text
    assert school_plan.status_code == 201, school_plan.text
    assert personal_plan.json()["id"] != school_plan.json()["id"]


def test_creating_a_weekly_plan_normalises_to_that_weeks_monday(client):
    owner, org_id, _ = create_school_class(client)
    plan = create_weekly_plan(client, owner, org_id)
    assert plan["week_start_date"] == _THAT_WEEKS_MONDAY


def test_creating_a_weekly_plan_twice_for_the_same_week_is_idempotent(client):
    owner, org_id, _ = create_school_class(client)
    first = create_weekly_plan(client, owner, org_id)
    second = create_weekly_plan(client, owner, org_id, week_start_date=_THAT_WEEKS_MONDAY)
    assert first["id"] == second["id"]


def test_get_by_week_404s_when_nothing_created_yet(client):
    owner, org_id, _ = create_school_class(client)
    res = client.get(
        f"/api/v1/organizations/{org_id}/weekly-plans", params={"week_start_date": _A_WEDNESDAY}, headers=auth_headers(owner)
    )
    assert res.status_code == 404


def test_get_by_week_finds_the_normalised_plan(client):
    owner, org_id, _ = create_school_class(client)
    create_weekly_plan(client, owner, org_id, week_start_date=_A_WEDNESDAY)
    res = client.get(
        f"/api/v1/organizations/{org_id}/weekly-plans", params={"week_start_date": "2026-09-18"}, headers=auth_headers(owner)
    )
    assert res.status_code == 200
    assert res.json()["week_start_date"] == _THAT_WEEKS_MONDAY


def test_add_item_and_see_it_reflected_in_the_plan(client):
    owner, org_id, class_id = create_school_class(client)
    plan = create_weekly_plan(client, owner, org_id)

    item = client.post(
        f"/api/v1/weekly-plans/{plan['id']}/items",
        json={"class_id": class_id, "day_of_week": "monday", "start_time": "09:00:00", "duration_minutes": 50, "topic_override": "Intro to atoms"},
        headers=auth_headers(owner),
    )
    assert item.status_code == 201, item.text
    body = item.json()
    assert body["class_name"] == "Year 10 Chemistry"
    assert body["topic"] == "Intro to atoms"

    detail = client.get(f"/api/v1/weekly-plans/{plan['id']}", headers=auth_headers(owner)).json()
    assert len(detail["items"]) == 1


def test_item_uses_linked_lesson_plan_topic_over_the_override(client):
    owner, org_id, class_id = create_school_class(client)
    lesson_plan = create_lesson_plan(client, owner, class_id, topic="Real topic from the lesson plan")
    plan = create_weekly_plan(client, owner, org_id)

    item = client.post(
        f"/api/v1/weekly-plans/{plan['id']}/items",
        json={
            "class_id": class_id,
            "lesson_plan_id": lesson_plan["id"],
            "day_of_week": "tuesday",
            "start_time": "10:00:00",
            "duration_minutes": 50,
            "topic_override": "This should be ignored",
        },
        headers=auth_headers(owner),
    )
    assert item.status_code == 201, item.text
    assert item.json()["topic"] == "Real topic from the lesson plan"
    assert item.json()["template_type"] == "standard"


def test_cannot_add_an_item_for_a_class_you_do_not_teach(client):
    owner, org_id, class_id = create_school_class(client)
    plan = create_weekly_plan(client, owner, org_id)

    colleague = register_teacher(client)
    client.post(
        f"/api/v1/organizations/{org_id}/members", json={"email": colleague["email"], "role": "teacher"}, headers=auth_headers(owner)
    )
    colleague_plan = create_weekly_plan(client, colleague, org_id)

    res = client.post(
        f"/api/v1/weekly-plans/{colleague_plan['id']}/items",
        json={"class_id": class_id, "day_of_week": "monday", "start_time": "09:00:00", "duration_minutes": 50},
        headers=auth_headers(colleague),
    )
    assert res.status_code == 400  # class_id belongs to owner, not colleague


def test_lesson_plan_must_belong_to_the_given_class(client):
    owner, org_id, class_id = create_school_class(client)
    other_class = client.post(
        f"/api/v1/organizations/{org_id}/classes",
        json={"name": "Year 11 Chemistry", "subject_name": "Chemistry", "year_group": "year_11", "qualification": "GCSE"},
        headers=auth_headers(owner),
    ).json()
    lesson_plan = create_lesson_plan(client, owner, class_id)
    plan = create_weekly_plan(client, owner, org_id)

    res = client.post(
        f"/api/v1/weekly-plans/{plan['id']}/items",
        json={
            "class_id": other_class["id"],
            "lesson_plan_id": lesson_plan["id"],  # belongs to the *first* class, not other_class
            "day_of_week": "monday",
            "start_time": "09:00:00",
            "duration_minutes": 50,
        },
        headers=auth_headers(owner),
    )
    assert res.status_code == 400


def test_weekly_plan_is_private_to_its_owning_teacher(client):
    owner, org_id, _ = create_school_class(client)
    plan = create_weekly_plan(client, owner, org_id)

    colleague = register_teacher(client)
    client.post(
        f"/api/v1/organizations/{org_id}/members", json={"email": colleague["email"], "role": "teacher"}, headers=auth_headers(owner)
    )

    res = client.get(f"/api/v1/weekly-plans/{plan['id']}", headers=auth_headers(colleague))
    assert res.status_code == 403


def test_changing_only_class_id_revalidates_an_existing_lesson_plan_link(client):
    """Regression test: an item linked to class A's lesson plan must not be
    silently left pointing at that lesson plan after its class_id is
    changed to class B without also clearing/updating lesson_plan_id.
    """
    owner, org_id, class_id = create_school_class(client)
    other_class = client.post(
        f"/api/v1/organizations/{org_id}/classes",
        json={"name": "Year 11 Chemistry", "subject_name": "Chemistry", "year_group": "year_11", "qualification": "GCSE"},
        headers=auth_headers(owner),
    ).json()
    lesson_plan = create_lesson_plan(client, owner, class_id)
    plan = create_weekly_plan(client, owner, org_id)
    item = client.post(
        f"/api/v1/weekly-plans/{plan['id']}/items",
        json={
            "class_id": class_id,
            "lesson_plan_id": lesson_plan["id"],
            "day_of_week": "monday",
            "start_time": "09:00:00",
            "duration_minutes": 50,
        },
        headers=auth_headers(owner),
    ).json()

    res = client.patch(
        f"/api/v1/weekly-plan-items/{item['id']}", json={"class_id": other_class["id"]}, headers=auth_headers(owner)
    )
    assert res.status_code == 400

    # The item must still show the original, consistent class/lesson-plan pairing.
    detail = client.get(f"/api/v1/weekly-plans/{plan['id']}", headers=auth_headers(owner)).json()
    assert detail["items"][0]["class_id"] == class_id
    assert detail["items"][0]["lesson_plan_id"] == lesson_plan["id"]


def test_update_and_delete_item(client):
    owner, org_id, class_id = create_school_class(client)
    plan = create_weekly_plan(client, owner, org_id)
    item = client.post(
        f"/api/v1/weekly-plans/{plan['id']}/items",
        json={"class_id": class_id, "day_of_week": "monday", "start_time": "09:00:00", "duration_minutes": 50},
        headers=auth_headers(owner),
    ).json()

    updated = client.patch(
        f"/api/v1/weekly-plan-items/{item['id']}", json={"duration_minutes": 60}, headers=auth_headers(owner)
    )
    assert updated.status_code == 200
    assert updated.json()["duration_minutes"] == 60

    deleted = client.delete(f"/api/v1/weekly-plan-items/{item['id']}", headers=auth_headers(owner))
    assert deleted.status_code == 204
    detail = client.get(f"/api/v1/weekly-plans/{plan['id']}", headers=auth_headers(owner)).json()
    assert detail["items"] == []


def test_deleting_a_class_cascades_to_its_weekly_plan_items(client, db_session):
    from app.models.weekly_plan import WeeklyPlanItem

    owner, org_id, class_id = create_school_class(client)
    plan = create_weekly_plan(client, owner, org_id)
    item = client.post(
        f"/api/v1/weekly-plans/{plan['id']}/items",
        json={"class_id": class_id, "day_of_week": "monday", "start_time": "09:00:00", "duration_minutes": 50},
        headers=auth_headers(owner),
    ).json()

    client.delete(f"/api/v1/classes/{class_id}", headers=auth_headers(owner))

    db_session.expire_all()
    import uuid as uuid_module

    assert db_session.get(WeeklyPlanItem, uuid_module.UUID(item["id"])) is None


def test_issues_surface_in_the_weekly_plan_detail(client):
    owner, org_id, class_id = create_school_class(client)
    plan = create_weekly_plan(client, owner, org_id)

    client.post(
        f"/api/v1/weekly-plans/{plan['id']}/items",
        json={"class_id": class_id, "day_of_week": "monday", "start_time": "09:00:00", "duration_minutes": 60},
        headers=auth_headers(owner),
    )
    client.post(
        f"/api/v1/weekly-plans/{plan['id']}/items",
        json={"class_id": class_id, "day_of_week": "monday", "start_time": "09:30:00", "duration_minutes": 30, "topic_override": "double booked"},
        headers=auth_headers(owner),
    )

    detail = client.get(f"/api/v1/weekly-plans/{plan['id']}", headers=auth_headers(owner)).json()
    categories = {i["category"] for i in detail["issues"]}
    assert "conflict" in categories
