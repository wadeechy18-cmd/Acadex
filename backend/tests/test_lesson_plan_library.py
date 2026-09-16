from app.core.security import hash_password
from app.models.curriculum import Curriculum, CurriculumTopic, KeyStage, ProgrammeOfStudy, Subject, YearGroup
from app.models.lesson_plan import AbilityLevel, GenerationKind, LessonPlan, LessonPlanVersion
from app.models.user import TeacherProfile, User, UserRole
from app.services.lesson_plan_service import LIBRARY_OWNER_EMAIL
from tests.conftest import auth_headers, register_teacher
from tests.test_lesson_plans import SAMPLE_CONTENT


def _seed_library_plan(db_session, *, topic_title="Fractions"):
    curriculum = Curriculum(code="ENC", name="English National Curriculum", country="England")
    db_session.add(curriculum)
    db_session.flush()
    key_stage = KeyStage(curriculum_id=curriculum.id, code="KS1", name="Key Stage 1", sort_order=1)
    db_session.add(key_stage)
    db_session.flush()
    year_group = YearGroup(key_stage_id=key_stage.id, code="Y2", name="Year 2", sort_order=1)
    subject = Subject(curriculum_id=curriculum.id, code="MATHS", name="Mathematics")
    db_session.add_all([year_group, subject])
    db_session.flush()
    pos = ProgrammeOfStudy(subject_id=subject.id, year_group_id=year_group.id)
    db_session.add(pos)
    db_session.flush()
    topic = CurriculumTopic(programme_of_study_id=pos.id, title=topic_title, sort_order=1)
    db_session.add(topic)
    db_session.flush()

    library_user = db_session.query(User).filter_by(email=LIBRARY_OWNER_EMAIL).first()
    if not library_user:
        library_user = User(email=LIBRARY_OWNER_EMAIL, hashed_password=hash_password("unused"), role=UserRole.TEACHER, is_active=False)
        db_session.add(library_user)
        db_session.flush()
        db_session.add(TeacherProfile(user_id=library_user.id, display_name="Acadex Curriculum Library"))
        db_session.flush()

    plan = LessonPlan(
        owner_user_id=library_user.id,
        subject_id=subject.id,
        year_group_id=year_group.id,
        curriculum_topic_id=topic.id,
        topic_title=topic_title,
        duration_minutes=30,
        ability_level=AbilityLevel.MIXED,
    )
    db_session.add(plan)
    db_session.flush()
    version = LessonPlanVersion(
        lesson_plan_id=plan.id,
        version_number=1,
        content=SAMPLE_CONTENT.model_dump(mode="json"),
        created_by_user_id=library_user.id,
        generation_kind=GenerationKind.MANUAL_EDIT,
        safeguarding_flagged=False,
    )
    db_session.add(version)
    db_session.commit()
    return plan, subject, year_group


def test_list_library_plans_is_visible_to_any_teacher(client, db_session):
    _seed_library_plan(db_session)
    teacher = register_teacher(client)

    res = client.get("/api/v1/lesson-plans/library", headers=auth_headers(teacher))
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["topic_title"] == "Fractions"


def test_list_library_plans_returns_empty_when_unseeded(client, db_session):
    teacher = register_teacher(client)
    res = client.get("/api/v1/lesson-plans/library", headers=auth_headers(teacher))
    assert res.status_code == 200
    assert res.json() == []


def test_library_plans_can_be_filtered_by_subject_and_topic(client, db_session):
    _seed_library_plan(db_session, topic_title="Fractions")
    teacher = register_teacher(client)

    match = client.get("/api/v1/lesson-plans/library", params={"topic": "fraction"}, headers=auth_headers(teacher))
    assert len(match.json()) == 1
    no_match = client.get("/api/v1/lesson-plans/library", params={"topic": "grammar"}, headers=auth_headers(teacher))
    assert no_match.json() == []


def test_get_library_plan_detail(client, db_session):
    plan, _subject, _year_group = _seed_library_plan(db_session)
    teacher = register_teacher(client)

    res = client.get(f"/api/v1/lesson-plans/library/{plan.id}", headers=auth_headers(teacher))
    assert res.status_code == 200
    assert res.json()["current_version"]["content"]["title"] == SAMPLE_CONTENT.title


def test_duplicate_library_plan_creates_an_independent_copy_owned_by_the_teacher(client, db_session):
    plan, _subject, _year_group = _seed_library_plan(db_session)
    teacher = register_teacher(client)

    res = client.post(f"/api/v1/lesson-plans/library/{plan.id}/duplicate", headers=auth_headers(teacher))
    assert res.status_code == 201, res.text
    copy = res.json()
    assert copy["id"] != str(plan.id)
    assert copy["current_version"]["content"]["title"] == SAMPLE_CONTENT.title

    # The teacher's own library now contains their copy, fully editable.
    mine = client.get("/api/v1/lesson-plans", headers=auth_headers(teacher))
    assert len(mine.json()) == 1
    assert mine.json()[0]["id"] == copy["id"]

    # The library original is untouched -- still owned by the library account.
    still_in_library = client.get("/api/v1/lesson-plans/library", headers=auth_headers(teacher))
    assert len(still_in_library.json()) == 1


def test_duplicate_nonexistent_library_plan_returns_404(client, db_session):
    teacher = register_teacher(client)
    res = client.post("/api/v1/lesson-plans/library/00000000-0000-0000-0000-000000000000/duplicate", headers=auth_headers(teacher))
    assert res.status_code == 404


def test_library_endpoints_require_authentication(client, db_session):
    _seed_library_plan(db_session)
    assert client.get("/api/v1/lesson-plans/library").status_code == 401
