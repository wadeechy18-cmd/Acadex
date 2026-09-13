from app.models.curriculum import Curriculum, KeyStage, ProgrammeOfStudy, Subject, YearGroup
from tests.conftest import auth_headers, register_school, register_teacher


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


def _school_with_teacher(client):
    admin = register_school(client, school_name="Timetable School")
    teacher = register_teacher(client)
    school_id = admin["school"]["id"]
    client.post(f"/api/v1/schools/{school_id}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(admin))
    return admin, teacher, school_id


def _setup_grid(client, admin, school_id):
    year = client.post(
        f"/api/v1/schools/{school_id}/academic-years",
        json={"name": "2025/2026", "start_date": "2025-09-01", "end_date": "2026-07-31"},
        headers=auth_headers(admin),
    ).json()
    room = client.post(f"/api/v1/schools/{school_id}/rooms", json={"name": "Room 1", "capacity": 30}, headers=auth_headers(admin)).json()
    slot = client.post(
        f"/api/v1/schools/{school_id}/time-slots",
        json={"day_of_week": 0, "start_time": "09:00:00", "end_time": "09:45:00", "label": "Period 1"},
        headers=auth_headers(admin),
    ).json()
    timetable = client.post(
        f"/api/v1/schools/{school_id}/timetables",
        json={"academic_year_id": year["id"], "name": "Main Timetable"},
        headers=auth_headers(admin),
    ).json()
    return year, room, slot, timetable


def test_admin_can_set_up_the_timetable_grid_and_add_an_entry(client, db_session):
    subject = _seed_subject(db_session)
    admin, teacher, school_id = _school_with_teacher(client)
    year, room, slot, timetable = _setup_grid(client, admin, school_id)

    entry = client.post(
        f"/api/v1/schools/{school_id}/timetables/{timetable['id']}/entries",
        json={"time_slot_id": slot["id"], "teacher_user_id": teacher["user"]["id"], "subject_id": str(subject.id), "room_id": room["id"]},
        headers=auth_headers(admin),
    )
    assert entry.status_code == 201, entry.text
    assert entry.json()["teacher_name"] == "Test Teacher"
    assert entry.json()["room_name"] == "Room 1"

    listing = client.get(f"/api/v1/schools/{school_id}/timetables/{timetable['id']}/entries", headers=auth_headers(admin))
    assert len(listing.json()) == 1


def test_cannot_double_book_a_teacher_in_the_same_slot(client, db_session):
    subject = _seed_subject(db_session)
    admin, teacher, school_id = _school_with_teacher(client)
    year, room, slot, timetable = _setup_grid(client, admin, school_id)
    other_room = client.post(f"/api/v1/schools/{school_id}/rooms", json={"name": "Room 2"}, headers=auth_headers(admin)).json()

    first = client.post(
        f"/api/v1/schools/{school_id}/timetables/{timetable['id']}/entries",
        json={"time_slot_id": slot["id"], "teacher_user_id": teacher["user"]["id"], "subject_id": str(subject.id), "room_id": room["id"]},
        headers=auth_headers(admin),
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/schools/{school_id}/timetables/{timetable['id']}/entries",
        json={"time_slot_id": slot["id"], "teacher_user_id": teacher["user"]["id"], "subject_id": str(subject.id), "room_id": other_room["id"]},
        headers=auth_headers(admin),
    )
    assert second.status_code == 409


def test_cannot_double_book_a_room_in_the_same_slot(client, db_session):
    subject = _seed_subject(db_session)
    admin, teacher, school_id = _school_with_teacher(client)
    other_teacher = register_teacher(client)
    client.post(
        f"/api/v1/schools/{school_id}/members", json={"email": other_teacher["email"], "role": "teacher"}, headers=auth_headers(admin)
    )
    year, room, slot, timetable = _setup_grid(client, admin, school_id)

    first = client.post(
        f"/api/v1/schools/{school_id}/timetables/{timetable['id']}/entries",
        json={"time_slot_id": slot["id"], "teacher_user_id": teacher["user"]["id"], "subject_id": str(subject.id), "room_id": room["id"]},
        headers=auth_headers(admin),
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/schools/{school_id}/timetables/{timetable['id']}/entries",
        json={"time_slot_id": slot["id"], "teacher_user_id": other_teacher["user"]["id"], "subject_id": str(subject.id), "room_id": room["id"]},
        headers=auth_headers(admin),
    )
    assert second.status_code == 409


def test_cannot_double_book_a_class_in_the_same_slot(client, db_session):
    subject = _seed_subject(db_session)
    admin, teacher, school_id = _school_with_teacher(client)
    other_teacher = register_teacher(client)
    client.post(
        f"/api/v1/schools/{school_id}/members", json={"email": other_teacher["email"], "role": "teacher"}, headers=auth_headers(admin)
    )
    year, room, slot, timetable = _setup_grid(client, admin, school_id)
    class_ = client.post("/api/v1/classes", json={"name": "Year 2A"}, headers=auth_headers(teacher)).json()

    first = client.post(
        f"/api/v1/schools/{school_id}/timetables/{timetable['id']}/entries",
        json={"time_slot_id": slot["id"], "teacher_user_id": teacher["user"]["id"], "subject_id": str(subject.id), "class_id": class_["id"]},
        headers=auth_headers(admin),
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/schools/{school_id}/timetables/{timetable['id']}/entries",
        json={
            "time_slot_id": slot["id"],
            "teacher_user_id": other_teacher["user"]["id"],
            "subject_id": str(subject.id),
            "class_id": class_["id"],
        },
        headers=auth_headers(admin),
    )
    assert second.status_code == 409


def test_updating_an_entry_does_not_conflict_with_itself(client, db_session):
    subject = _seed_subject(db_session)
    admin, teacher, school_id = _school_with_teacher(client)
    year, room, slot, timetable = _setup_grid(client, admin, school_id)

    entry = client.post(
        f"/api/v1/schools/{school_id}/timetables/{timetable['id']}/entries",
        json={"time_slot_id": slot["id"], "teacher_user_id": teacher["user"]["id"], "subject_id": str(subject.id), "room_id": room["id"]},
        headers=auth_headers(admin),
    ).json()

    update = client.patch(
        f"/api/v1/schools/{school_id}/timetables/{timetable['id']}/entries/{entry['id']}",
        json={"time_slot_id": slot["id"], "teacher_user_id": teacher["user"]["id"], "subject_id": str(subject.id), "room_id": room["id"]},
        headers=auth_headers(admin),
    )
    assert update.status_code == 200


def test_cannot_assign_a_teacher_outside_the_school_to_an_entry(client, db_session):
    subject = _seed_subject(db_session)
    admin, teacher, school_id = _school_with_teacher(client)
    outsider = register_teacher(client)
    year, room, slot, timetable = _setup_grid(client, admin, school_id)

    res = client.post(
        f"/api/v1/schools/{school_id}/timetables/{timetable['id']}/entries",
        json={"time_slot_id": slot["id"], "teacher_user_id": outsider["user"]["id"], "subject_id": str(subject.id)},
        headers=auth_headers(admin),
    )
    assert res.status_code == 400


def test_plain_teacher_cannot_create_timetable_entries(client, db_session):
    subject = _seed_subject(db_session)
    admin, teacher, school_id = _school_with_teacher(client)
    year, room, slot, timetable = _setup_grid(client, admin, school_id)

    res = client.post(
        f"/api/v1/schools/{school_id}/timetables/{timetable['id']}/entries",
        json={"time_slot_id": slot["id"], "teacher_user_id": teacher["user"]["id"], "subject_id": str(subject.id)},
        headers=auth_headers(teacher),
    )
    assert res.status_code == 403


def test_qualifications_add_list_and_remove(client, db_session):
    subject = _seed_subject(db_session)
    admin, teacher, school_id = _school_with_teacher(client)

    add = client.post(
        f"/api/v1/schools/{school_id}/teachers/{teacher['user']['id']}/qualifications",
        json={"subject_id": str(subject.id)},
        headers=auth_headers(admin),
    )
    assert add.status_code == 201
    qualification_id = add.json()["id"]

    listing = client.get(f"/api/v1/schools/{school_id}/teachers/{teacher['user']['id']}/qualifications", headers=auth_headers(admin))
    assert len(listing.json()) == 1

    remove = client.delete(f"/api/v1/schools/{school_id}/qualifications/{qualification_id}", headers=auth_headers(admin))
    assert remove.status_code == 204


def test_teacher_can_set_their_own_availability_but_not_someone_elses(client, db_session):
    admin, teacher, school_id = _school_with_teacher(client)
    other_teacher = register_teacher(client)
    client.post(
        f"/api/v1/schools/{school_id}/members", json={"email": other_teacher["email"], "role": "teacher"}, headers=auth_headers(admin)
    )
    slot = client.post(
        f"/api/v1/schools/{school_id}/time-slots",
        json={"day_of_week": 0, "start_time": "09:00:00", "end_time": "09:45:00", "label": "Period 1"},
        headers=auth_headers(admin),
    ).json()

    own = client.put(
        f"/api/v1/schools/{school_id}/teachers/{teacher['user']['id']}/availability",
        json={"time_slot_id": slot["id"], "status": "unavailable"},
        headers=auth_headers(teacher),
    )
    assert own.status_code == 200
    assert own.json()["status"] == "unavailable"

    forbidden = client.put(
        f"/api/v1/schools/{school_id}/teachers/{other_teacher['user']['id']}/availability",
        json={"time_slot_id": slot["id"], "status": "unavailable"},
        headers=auth_headers(teacher),
    )
    assert forbidden.status_code == 403

    admin_set = client.put(
        f"/api/v1/schools/{school_id}/teachers/{other_teacher['user']['id']}/availability",
        json={"time_slot_id": slot["id"], "status": "unavailable"},
        headers=auth_headers(admin),
    )
    assert admin_set.status_code == 200


def test_timetable_endpoints_are_isolated_between_schools(client, db_session):
    subject = _seed_subject(db_session)
    admin_a, teacher_a, school_a = _school_with_teacher(client)
    admin_b = register_school(client, school_name="Other Timetable School")

    res = client.get(f"/api/v1/schools/{school_a}/rooms", headers=auth_headers(admin_b))
    assert res.status_code == 403
