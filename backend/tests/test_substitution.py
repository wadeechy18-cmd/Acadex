from datetime import date, timedelta

from app.models.curriculum import Curriculum, KeyStage, ProgrammeOfStudy, Subject, YearGroup
from tests.conftest import auth_headers, register_school, register_teacher


def _next_weekday(target_weekday: int) -> date:
    today = date.today()
    days_ahead = (target_weekday - today.weekday()) % 7
    days_ahead = days_ahead or 7
    return today + timedelta(days=days_ahead)


def _seed_subject(db_session):
    curriculum = Curriculum(code="ENC", name="English National Curriculum", country="England")
    db_session.add(curriculum)
    db_session.flush()
    key_stage = KeyStage(curriculum_id=curriculum.id, code="KS1", name="Key Stage 1", sort_order=1)
    db_session.add(key_stage)
    db_session.flush()
    year_group = YearGroup(key_stage_id=key_stage.id, code="Y2", name="Year 2", sort_order=1)
    db_session.add(year_group)
    db_session.flush()
    maths = Subject(curriculum_id=curriculum.id, code="MATHS", name="Mathematics")
    db_session.add(maths)
    db_session.flush()
    db_session.add(ProgrammeOfStudy(subject_id=maths.id, year_group_id=year_group.id))
    db_session.commit()
    return maths, year_group


def _setup_school_with_timetable(client, db_session, num_extra_teachers=1):
    subject, year_group = _seed_subject(db_session)
    admin = register_school(client, school_name="Sub School")
    absent_teacher = register_teacher(client)
    school_id = admin["school"]["id"]
    client.post(f"/api/v1/schools/{school_id}/members", json={"email": absent_teacher["email"], "role": "teacher"}, headers=auth_headers(admin))

    extra_teachers = []
    for _ in range(num_extra_teachers):
        t = register_teacher(client)
        client.post(f"/api/v1/schools/{school_id}/members", json={"email": t["email"], "role": "teacher"}, headers=auth_headers(admin))
        extra_teachers.append(t)

    year = client.post(
        f"/api/v1/schools/{school_id}/academic-years",
        json={"name": "Wide Year", "start_date": "2020-01-01", "end_date": "2035-12-31"},
        headers=auth_headers(admin),
    ).json()
    slot = client.post(
        f"/api/v1/schools/{school_id}/time-slots",
        json={"day_of_week": 0, "start_time": "09:00:00", "end_time": "09:45:00", "label": "Period 1"},
        headers=auth_headers(admin),
    ).json()
    timetable = client.post(
        f"/api/v1/schools/{school_id}/timetables",
        json={"academic_year_id": year["id"], "name": "Main"},
        headers=auth_headers(admin),
    ).json()
    client.post(
        f"/api/v1/schools/{school_id}/timetables/{timetable['id']}/entries",
        json={"time_slot_id": slot["id"], "teacher_user_id": absent_teacher["user"]["id"], "subject_id": str(subject.id)},
        headers=auth_headers(admin),
    )

    return {
        "admin": admin,
        "absent_teacher": absent_teacher,
        "extra_teachers": extra_teachers,
        "school_id": school_id,
        "subject": subject,
        "year_group": year_group,
        "slot": slot,
        "timetable": timetable,
    }


def _report_absence(client, ctx):
    monday = _next_weekday(0)
    return client.post(
        f"/api/v1/schools/{ctx['school_id']}/absences",
        json={"teacher_user_id": ctx["absent_teacher"]["user"]["id"], "date": str(monday)},
        headers=auth_headers(ctx["admin"]),
    ).json()


def test_generate_plan_assigns_an_available_teacher(client, db_session):
    ctx = _setup_school_with_timetable(client, db_session, num_extra_teachers=1)
    absence = _report_absence(client, ctx)

    res = client.post(
        f"/api/v1/schools/{ctx['school_id']}/absences/{absence['id']}/substitution-plan/generate", headers=auth_headers(ctx["admin"])
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "proposed"
    assert len(body["assignments"]) == 1
    assignment = body["assignments"][0]
    assert assignment["status"] == "assigned"
    assert assignment["substitute_teacher_user_id"] == ctx["extra_teachers"][0]["user"]["id"]


def test_generate_plan_leaves_lesson_unfilled_when_no_teacher_is_available(client, db_session):
    ctx = _setup_school_with_timetable(client, db_session, num_extra_teachers=0)
    absence = _report_absence(client, ctx)

    res = client.post(
        f"/api/v1/schools/{ctx['school_id']}/absences/{absence['id']}/substitution-plan/generate", headers=auth_headers(ctx["admin"])
    )
    assert res.status_code == 201
    assignment = res.json()["assignments"][0]
    assert assignment["status"] == "unfilled"
    assert assignment["reason"] is not None


def test_generate_plan_never_assigns_a_teacher_marked_unavailable(client, db_session):
    ctx = _setup_school_with_timetable(client, db_session, num_extra_teachers=1)
    candidate = ctx["extra_teachers"][0]
    client.put(
        f"/api/v1/schools/{ctx['school_id']}/teachers/{candidate['user']['id']}/availability",
        json={"time_slot_id": ctx["slot"]["id"], "status": "unavailable"},
        headers=auth_headers(candidate),
    )
    absence = _report_absence(client, ctx)

    res = client.post(
        f"/api/v1/schools/{ctx['school_id']}/absences/{absence['id']}/substitution-plan/generate", headers=auth_headers(ctx["admin"])
    )
    assignment = res.json()["assignments"][0]
    assert assignment["status"] == "unfilled"


def test_generate_plan_never_assigns_a_teacher_already_busy_at_that_slot(client, db_session):
    ctx = _setup_school_with_timetable(client, db_session, num_extra_teachers=1)
    candidate = ctx["extra_teachers"][0]
    # Busy the candidate at the same slot with their own lesson
    client.post(
        f"/api/v1/schools/{ctx['school_id']}/timetables/{ctx['timetable']['id']}/entries",
        json={"time_slot_id": ctx["slot"]["id"], "teacher_user_id": candidate["user"]["id"], "subject_id": str(ctx["subject"].id)},
        headers=auth_headers(ctx["admin"]),
    )
    absence = _report_absence(client, ctx)

    res = client.post(
        f"/api/v1/schools/{ctx['school_id']}/absences/{absence['id']}/substitution-plan/generate", headers=auth_headers(ctx["admin"])
    )
    assignment = res.json()["assignments"][0]
    assert assignment["status"] == "unfilled"


def test_prefers_a_qualified_teacher_when_choosing_between_candidates(client, db_session):
    ctx = _setup_school_with_timetable(client, db_session, num_extra_teachers=2)
    qualified, unqualified = ctx["extra_teachers"]
    client.post(
        f"/api/v1/schools/{ctx['school_id']}/teachers/{qualified['user']['id']}/qualifications",
        json={"subject_id": str(ctx["subject"].id)},
        headers=auth_headers(ctx["admin"]),
    )
    absence = _report_absence(client, ctx)

    res = client.post(
        f"/api/v1/schools/{ctx['school_id']}/absences/{absence['id']}/substitution-plan/generate", headers=auth_headers(ctx["admin"])
    )
    assignment = res.json()["assignments"][0]
    assert assignment["substitute_teacher_user_id"] == qualified["user"]["id"]


def test_regenerating_a_plan_replaces_the_previous_one(client, db_session):
    ctx = _setup_school_with_timetable(client, db_session, num_extra_teachers=1)
    absence = _report_absence(client, ctx)

    first = client.post(
        f"/api/v1/schools/{ctx['school_id']}/absences/{absence['id']}/substitution-plan/generate", headers=auth_headers(ctx["admin"])
    ).json()
    second = client.post(
        f"/api/v1/schools/{ctx['school_id']}/absences/{absence['id']}/substitution-plan/generate", headers=auth_headers(ctx["admin"])
    ).json()
    assert first["id"] != second["id"]

    fetched = client.get(f"/api/v1/schools/{ctx['school_id']}/absences/{absence['id']}/substitution-plan", headers=auth_headers(ctx["admin"]))
    assert fetched.json()["id"] == second["id"]


def test_admin_can_manually_reassign_before_approval(client, db_session):
    ctx = _setup_school_with_timetable(client, db_session, num_extra_teachers=2)
    plan = client.post(
        f"/api/v1/schools/{ctx['school_id']}/absences/{_report_absence(client, ctx)['id']}/substitution-plan/generate",
        headers=auth_headers(ctx["admin"]),
    ).json()
    assignment_id = plan["assignments"][0]["id"]
    other_teacher = ctx["extra_teachers"][1] if plan["assignments"][0]["substitute_teacher_user_id"] == ctx["extra_teachers"][0]["user"]["id"] else ctx["extra_teachers"][0]

    res = client.patch(
        f"/api/v1/schools/{ctx['school_id']}/substitution-assignments/{assignment_id}",
        json={"substitute_teacher_user_id": other_teacher["user"]["id"]},
        headers=auth_headers(ctx["admin"]),
    )
    assert res.status_code == 200
    assert res.json()["substitute_teacher_user_id"] == other_teacher["user"]["id"]


def test_admin_can_manually_unassign(client, db_session):
    ctx = _setup_school_with_timetable(client, db_session, num_extra_teachers=1)
    plan = client.post(
        f"/api/v1/schools/{ctx['school_id']}/absences/{_report_absence(client, ctx)['id']}/substitution-plan/generate",
        headers=auth_headers(ctx["admin"]),
    ).json()
    assignment_id = plan["assignments"][0]["id"]

    res = client.patch(
        f"/api/v1/schools/{ctx['school_id']}/substitution-assignments/{assignment_id}",
        json={"substitute_teacher_user_id": None},
        headers=auth_headers(ctx["admin"]),
    )
    assert res.status_code == 200
    assert res.json()["status"] == "unfilled"


def test_approving_a_plan_creates_timetable_exceptions_and_notifies_the_substitute(client, db_session):
    ctx = _setup_school_with_timetable(client, db_session, num_extra_teachers=1)
    absence = _report_absence(client, ctx)
    plan = client.post(
        f"/api/v1/schools/{ctx['school_id']}/absences/{absence['id']}/substitution-plan/generate", headers=auth_headers(ctx["admin"])
    ).json()

    approve = client.post(f"/api/v1/schools/{ctx['school_id']}/substitution-plans/{plan['id']}/approve", headers=auth_headers(ctx["admin"]))
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    substitute = ctx["extra_teachers"][0]
    my_cover = client.get("/api/v1/timetable-exceptions/mine", headers=auth_headers(substitute))
    assert my_cover.status_code == 200
    assert len(my_cover.json()) == 1
    assert my_cover.json()[0]["subject_name"] == "Mathematics"

    notifications = client.get("/api/v1/notifications/mine", headers=auth_headers(substitute))
    assert len(notifications.json()) == 1
    assert notifications.json()[0]["read_at"] is None


def test_substitute_sees_the_absent_teachers_lesson_plan_in_cover_view(client, db_session):
    from tests.test_lesson_plans import SAMPLE_CONTENT, override_ai_provider, clear_ai_override

    ctx = _setup_school_with_timetable(client, db_session, num_extra_teachers=1)

    class_res = client.post("/api/v1/classes", json={"name": "Year 2A"}, headers=auth_headers(ctx["absent_teacher"])).json()
    # Rebuild the timetable entry to include the class this time (original had no class_id)
    entries = client.get(f"/api/v1/schools/{ctx['school_id']}/timetables/{ctx['timetable']['id']}/entries", headers=auth_headers(ctx["admin"])).json()
    client.patch(
        f"/api/v1/schools/{ctx['school_id']}/timetables/{ctx['timetable']['id']}/entries/{entries[0]['id']}",
        json={
            "time_slot_id": ctx["slot"]["id"],
            "teacher_user_id": ctx["absent_teacher"]["user"]["id"],
            "subject_id": str(ctx["subject"].id),
            "class_id": class_res["id"],
        },
        headers=auth_headers(ctx["admin"]),
    )

    override_ai_provider(SAMPLE_CONTENT)
    generated = client.post(
        "/api/v1/lesson-plans/generate",
        json={
            "subject_id": str(ctx["subject"].id),
            "year_group_id": str(ctx["year_group"].id),
            "topic_title": "Fractions",
            "duration_minutes": 45,
            "ability_level": "mixed",
        },
        headers=auth_headers(ctx["absent_teacher"]),
    )
    clear_ai_override()
    assert generated.status_code == 201, generated.text
    client.patch(
        f"/api/v1/lesson-plans/{generated.json()['id']}/assign",
        json={"class_id": class_res["id"]},
        headers=auth_headers(ctx["absent_teacher"]),
    )

    absence = _report_absence(client, ctx)
    plan = client.post(
        f"/api/v1/schools/{ctx['school_id']}/absences/{absence['id']}/substitution-plan/generate", headers=auth_headers(ctx["admin"])
    ).json()
    client.post(f"/api/v1/schools/{ctx['school_id']}/substitution-plans/{plan['id']}/approve", headers=auth_headers(ctx["admin"]))

    substitute = ctx["extra_teachers"][0]
    my_cover = client.get("/api/v1/timetable-exceptions/mine", headers=auth_headers(substitute)).json()
    assert my_cover[0]["cover_lesson_plan_message"] is not None


def test_rejecting_a_plan_creates_no_exceptions(client, db_session):
    ctx = _setup_school_with_timetable(client, db_session, num_extra_teachers=1)
    absence = _report_absence(client, ctx)
    plan = client.post(
        f"/api/v1/schools/{ctx['school_id']}/absences/{absence['id']}/substitution-plan/generate", headers=auth_headers(ctx["admin"])
    ).json()

    reject = client.post(f"/api/v1/schools/{ctx['school_id']}/substitution-plans/{plan['id']}/reject", headers=auth_headers(ctx["admin"]))
    assert reject.status_code == 200
    assert reject.json()["status"] == "rejected"

    substitute = ctx["extra_teachers"][0]
    assert client.get("/api/v1/timetable-exceptions/mine", headers=auth_headers(substitute)).json() == []


def test_plain_teacher_cannot_generate_or_approve_a_plan(client, db_session):
    ctx = _setup_school_with_timetable(client, db_session, num_extra_teachers=1)
    absence = _report_absence(client, ctx)

    res = client.post(
        f"/api/v1/schools/{ctx['school_id']}/absences/{absence['id']}/substitution-plan/generate", headers=auth_headers(ctx["absent_teacher"])
    )
    assert res.status_code == 403


def test_substitution_endpoints_are_isolated_between_schools(client, db_session):
    ctx = _setup_school_with_timetable(client, db_session, num_extra_teachers=1)
    absence = _report_absence(client, ctx)
    plan = client.post(
        f"/api/v1/schools/{ctx['school_id']}/absences/{absence['id']}/substitution-plan/generate", headers=auth_headers(ctx["admin"])
    ).json()

    other_admin = register_school(client, school_name="Other Sub School")
    res = client.post(f"/api/v1/schools/{ctx['school_id']}/substitution-plans/{plan['id']}/approve", headers=auth_headers(other_admin))
    assert res.status_code == 403
