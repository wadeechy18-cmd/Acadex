from app.models.curriculum import Curriculum, CurriculumTopic, Objective, ProgrammeOfStudy, Subject, YearGroup
from scripts.seed_curriculum import run as run_seed


def test_seed_curriculum_is_idempotent_and_builds_the_expected_shape(db_session, monkeypatch):
    monkeypatch.setattr("scripts.seed_curriculum.SessionLocal", lambda: db_session)
    # SAVEPOINT-per-test rollback relies on the app never closing this session.
    monkeypatch.setattr(db_session, "close", lambda: None)

    run_seed()

    curriculum = db_session.query(Curriculum).filter_by(code="ENC").one()
    assert curriculum.country == "England"

    year_group_codes = {yg.code for yg in db_session.query(YearGroup).all()}
    assert {"RECEPTION", "Y1", "Y2"} <= year_group_codes

    maths = db_session.query(Subject).filter_by(curriculum_id=curriculum.id, code="MATHS").one()
    programmes_for_maths = db_session.query(ProgrammeOfStudy).filter_by(subject_id=maths.id).count()
    assert programmes_for_maths == 3  # Reception, Y1, Y2 all teach maths

    topics_before = db_session.query(CurriculumTopic).count()
    objectives_before = db_session.query(Objective).count()
    assert topics_before > 0
    assert objectives_before > 0

    run_seed()  # re-running must not duplicate anything

    assert db_session.query(CurriculumTopic).count() == topics_before
    assert db_session.query(Objective).count() == objectives_before
    assert db_session.query(Curriculum).filter_by(code="ENC").count() == 1
