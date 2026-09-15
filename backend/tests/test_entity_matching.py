from app.models.curriculum import Curriculum, KeyStage, Subject, YearGroup
from app.planning.entity_matching import match_subject, match_year_group


def _seed(db_session):
    curriculum = Curriculum(code="ENC", name="English National Curriculum", country="England")
    db_session.add(curriculum)
    db_session.flush()

    eyfs = KeyStage(curriculum_id=curriculum.id, code="EYFS", name="Early Years Foundation Stage", sort_order=0)
    ks1 = KeyStage(curriculum_id=curriculum.id, code="KS1", name="Key Stage 1", sort_order=1)
    db_session.add_all([eyfs, ks1])
    db_session.flush()

    reception = YearGroup(key_stage_id=eyfs.id, code="R", name="Reception", sort_order=0)
    year1 = YearGroup(key_stage_id=ks1.id, code="Y1", name="Year 1", sort_order=1)
    year2 = YearGroup(key_stage_id=ks1.id, code="Y2", name="Year 2", sort_order=2)
    db_session.add_all([reception, year1, year2])

    science = Subject(curriculum_id=curriculum.id, code="SCI", name="Science")
    maths = Subject(curriculum_id=curriculum.id, code="MATHS", name="Mathematics")
    db_session.add_all([science, maths])
    db_session.commit()

    return {"curriculum": curriculum, "reception": reception, "year1": year1, "year2": year2, "science": science, "maths": maths}


def test_match_subject_by_exact_and_partial_name(db_session):
    seed = _seed(db_session)
    assert match_subject(db_session, seed["curriculum"].id, "Science").id == seed["science"].id
    assert match_subject(db_session, seed["curriculum"].id, "science lesson").id == seed["science"].id
    assert match_subject(db_session, seed["curriculum"].id, "maths") is not None


def test_match_subject_returns_none_when_unrecognized(db_session):
    seed = _seed(db_session)
    assert match_subject(db_session, seed["curriculum"].id, "underwater basket weaving") is None
    assert match_subject(db_session, seed["curriculum"].id, None) is None


def test_match_year_group_by_various_phrasings(db_session):
    seed = _seed(db_session)
    assert match_year_group(db_session, seed["curriculum"].id, "Year 2").id == seed["year2"].id
    assert match_year_group(db_session, seed["curriculum"].id, "y2").id == seed["year2"].id
    assert match_year_group(db_session, seed["curriculum"].id, "a year 2 lesson").id == seed["year2"].id


def test_match_year_group_resolves_early_years_aliases(db_session):
    seed = _seed(db_session)
    assert match_year_group(db_session, seed["curriculum"].id, "early years").id == seed["reception"].id
    assert match_year_group(db_session, seed["curriculum"].id, "EYFS").id == seed["reception"].id
    assert match_year_group(db_session, seed["curriculum"].id, "reception class").id == seed["reception"].id


def test_match_year_group_returns_none_when_unrecognized(db_session):
    seed = _seed(db_session)
    assert match_year_group(db_session, seed["curriculum"].id, "sixth form") is None
