from datetime import date, timedelta

from app.models.curriculum import Curriculum, KeyStage, ProgrammeOfStudy, Subject, YearGroup
from tests.conftest import auth_headers, register_school, register_teacher


def _next_weekday(target_weekday: int) -> date:
    today = date.today()
    days_ahead = (target_weekday - today.weekday()) % 7
    days_ahead = days_ahead or 7
    return today + timedelta(days=days_ahead)


def _next_saturday() -> date:
    today = date.today()
    days_ahead = (5 - today.weekday()) % 7
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
    return maths


def _full_setup(client, db_session):
    """A school with one teacher and one timetable entry on Monday Period 1,
    with the academic year spanning a wide date range that includes
    upcoming Mondays.
    """
    subject = _seed_subject(db_session)
    admin = register_school(client, school_name="Absence School")
    teacher = register_teacher(client)
    school_id = admin["school"]["id"]
    client.post(f"/api/v1/schools/{school_id}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(admin))

    year = client.post(
        f"/api/v1/schools/{school_id}/academic-years",
        json={"name": "This Year", "start_date": "2020-01-01", "end_date": "2035-12-31"},
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
        json={"time_slot_id": slot["id"], "teacher_user_id": teacher["user"]["id"], "subject_id": str(subject.id)},
        headers=auth_headers(admin),
    )
    return admin, teacher, school_id


def test_reporting_an_absence_computes_affected_lessons_from_the_timetable(client, db_session):
    admin, teacher, school_id = _full_setup(client, db_session)
    monday = _next_weekday(0)

    res = client.post(
        f"/api/v1/schools/{school_id}/absences",
        json={"teacher_user_id": teacher["user"]["id"], "date": str(monday), "reason": "Sick"},
        headers=auth_headers(admin),
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert len(body["affected_lessons"]) == 1
    assert body["affected_lessons"][0]["subject_name"] == "Mathematics"
    assert body["affected_lessons"][0]["time_slot_label"] == "Period 1"


def test_absence_on_a_day_with_no_lessons_has_no_affected_lessons(client, db_session):
    admin, teacher, school_id = _full_setup(client, db_session)
    tuesday = _next_weekday(1)  # timetable entry is only on Monday

    res = client.post(
        f"/api/v1/schools/{school_id}/absences",
        json={"teacher_user_id": teacher["user"]["id"], "date": str(tuesday)},
        headers=auth_headers(admin),
    )
    assert res.status_code == 201
    assert res.json()["affected_lessons"] == []


def test_absence_on_a_weekend_has_no_affected_lessons(client, db_session):
    admin, teacher, school_id = _full_setup(client, db_session)
    saturday = _next_saturday()

    res = client.post(
        f"/api/v1/schools/{school_id}/absences",
        json={"teacher_user_id": teacher["user"]["id"], "date": str(saturday)},
        headers=auth_headers(admin),
    )
    assert res.status_code == 201
    assert res.json()["affected_lessons"] == []


def test_cannot_report_a_duplicate_absence_for_the_same_teacher_and_date(client, db_session):
    admin, teacher, school_id = _full_setup(client, db_session)
    monday = _next_weekday(0)

    first = client.post(
        f"/api/v1/schools/{school_id}/absences",
        json={"teacher_user_id": teacher["user"]["id"], "date": str(monday)},
        headers=auth_headers(admin),
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/schools/{school_id}/absences",
        json={"teacher_user_id": teacher["user"]["id"], "date": str(monday)},
        headers=auth_headers(admin),
    )
    assert second.status_code == 409


def test_cannot_report_an_absence_for_a_teacher_outside_the_school(client, db_session):
    admin, teacher, school_id = _full_setup(client, db_session)
    outsider = register_teacher(client)
    monday = _next_weekday(0)

    res = client.post(
        f"/api/v1/schools/{school_id}/absences",
        json={"teacher_user_id": outsider["user"]["id"], "date": str(monday)},
        headers=auth_headers(admin),
    )
    assert res.status_code == 400


def test_plain_teacher_cannot_report_an_absence(client, db_session):
    admin, teacher, school_id = _full_setup(client, db_session)
    monday = _next_weekday(0)

    res = client.post(
        f"/api/v1/schools/{school_id}/absences",
        json={"teacher_user_id": teacher["user"]["id"], "date": str(monday)},
        headers=auth_headers(teacher),
    )
    assert res.status_code == 403


def test_list_get_and_delete_absence(client, db_session):
    admin, teacher, school_id = _full_setup(client, db_session)
    monday = _next_weekday(0)
    created = client.post(
        f"/api/v1/schools/{school_id}/absences",
        json={"teacher_user_id": teacher["user"]["id"], "date": str(monday)},
        headers=auth_headers(admin),
    ).json()

    listing = client.get(f"/api/v1/schools/{school_id}/absences", headers=auth_headers(admin))
    assert len(listing.json()) == 1

    get_res = client.get(f"/api/v1/schools/{school_id}/absences/{created['id']}", headers=auth_headers(admin))
    assert get_res.status_code == 200

    delete_res = client.delete(f"/api/v1/schools/{school_id}/absences/{created['id']}", headers=auth_headers(admin))
    assert delete_res.status_code == 204
    assert client.get(f"/api/v1/schools/{school_id}/absences", headers=auth_headers(admin)).json() == []


def test_absences_are_isolated_between_schools(client, db_session):
    admin_a, teacher_a, school_a = _full_setup(client, db_session)
    admin_b = register_school(client, school_name="Other Absence School")

    res = client.get(f"/api/v1/schools/{school_a}/absences", headers=auth_headers(admin_b))
    assert res.status_code == 403
