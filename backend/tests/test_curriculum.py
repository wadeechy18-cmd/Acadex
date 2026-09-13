from app.models.curriculum import Curriculum, CurriculumTopic, KeyStage, Objective, ProgrammeOfStudy, Subject, YearGroup
from tests.conftest import auth_headers, register_teacher


def _seed_minimal_curriculum(db_session):
    curriculum = Curriculum(code="ENC", name="English National Curriculum", country="England")
    db_session.add(curriculum)
    db_session.flush()

    key_stage = KeyStage(curriculum_id=curriculum.id, code="KS1", name="Key Stage 1", sort_order=1)
    db_session.add(key_stage)
    db_session.flush()

    year_group = YearGroup(key_stage_id=key_stage.id, code="Y2", name="Year 2", sort_order=1)
    db_session.add(year_group)
    db_session.flush()

    other_year_group = YearGroup(key_stage_id=key_stage.id, code="Y1", name="Year 1", sort_order=0)
    db_session.add(other_year_group)
    db_session.flush()

    maths = Subject(curriculum_id=curriculum.id, code="MATHS", name="Mathematics")
    db_session.add(maths)
    db_session.flush()

    pos_y2 = ProgrammeOfStudy(subject_id=maths.id, year_group_id=year_group.id)
    db_session.add(pos_y2)
    db_session.flush()

    topic = CurriculumTopic(programme_of_study_id=pos_y2.id, title="Counting to 100", sort_order=1)
    db_session.add(topic)
    db_session.flush()

    objective = Objective(curriculum_topic_id=topic.id, code="MATHS.N1", description="Count forwards and backwards within 100.")
    db_session.add(objective)
    db_session.commit()

    return {
        "curriculum": curriculum,
        "key_stage": key_stage,
        "year_group": year_group,
        "other_year_group": other_year_group,
        "subject": maths,
        "topic": topic,
        "objective": objective,
    }


def test_full_browse_chain(client, db_session):
    seed = _seed_minimal_curriculum(db_session)
    teacher = register_teacher(client)
    headers = auth_headers(teacher)

    curricula = client.get("/api/v1/curriculum/curricula", headers=headers)
    assert curricula.status_code == 200
    assert any(c["code"] == "ENC" for c in curricula.json())

    key_stages = client.get(f"/api/v1/curriculum/curricula/{seed['curriculum'].id}/key-stages", headers=headers)
    assert key_stages.status_code == 200
    assert [k["code"] for k in key_stages.json()] == ["KS1"]

    year_groups = client.get(f"/api/v1/curriculum/key-stages/{seed['key_stage'].id}/year-groups", headers=headers)
    assert year_groups.status_code == 200
    assert [y["code"] for y in year_groups.json()] == ["Y1", "Y2"]

    subjects = client.get(f"/api/v1/curriculum/year-groups/{seed['year_group'].id}/subjects", headers=headers)
    assert subjects.status_code == 200
    assert [s["code"] for s in subjects.json()] == ["MATHS"]

    all_subjects = client.get(f"/api/v1/curriculum/curricula/{seed['curriculum'].id}/subjects", headers=headers)
    assert all_subjects.status_code == 200
    assert [s["code"] for s in all_subjects.json()] == ["MATHS"]

    topics = client.get(
        "/api/v1/curriculum/topics",
        params={"subject_id": str(seed["subject"].id), "year_group_id": str(seed["year_group"].id)},
        headers=headers,
    )
    assert topics.status_code == 200
    assert topics.json()[0]["title"] == "Counting to 100"

    objectives = client.get(f"/api/v1/curriculum/topics/{seed['topic'].id}/objectives", headers=headers)
    assert objectives.status_code == 200
    assert objectives.json()[0]["code"] == "MATHS.N1"


def test_subjects_are_scoped_to_year_group_with_a_programme_of_study(client, db_session):
    seed = _seed_minimal_curriculum(db_session)
    teacher = register_teacher(client)
    headers = auth_headers(teacher)

    subjects = client.get(f"/api/v1/curriculum/year-groups/{seed['other_year_group'].id}/subjects", headers=headers)
    assert subjects.status_code == 200
    assert subjects.json() == []


def test_topics_for_unknown_subject_year_group_pair_returns_404(client, db_session):
    _seed_minimal_curriculum(db_session)
    teacher = register_teacher(client)
    import uuid

    res = client.get(
        "/api/v1/curriculum/topics",
        params={"subject_id": str(uuid.uuid4()), "year_group_id": str(uuid.uuid4())},
        headers=auth_headers(teacher),
    )
    assert res.status_code == 404


def test_curriculum_endpoints_require_authentication(client):
    res = client.get("/api/v1/curriculum/curricula")
    assert res.status_code == 401
