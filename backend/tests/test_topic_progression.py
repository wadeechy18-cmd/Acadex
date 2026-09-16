from app.models.curriculum import Curriculum, CurriculumTopic, KeyStage, ProgrammeOfStudy, Subject, YearGroup
from app.models.lesson_plan import AbilityLevel, LessonPlan
from app.models.user import User
from app.schemas.quick_lesson import QuickLessonIntent
from app.services.lesson_plan_service import list_topic_progress, suggest_topic_progression
from tests.conftest import auth_headers, register_teacher
from tests.test_lesson_plans import SAMPLE_CONTENT, clear_ai_override, override_ai_provider


def _seed_sequence(db_session, count: int = 3):
    curriculum = Curriculum(code="ENC", name="English National Curriculum", country="England")
    db_session.add(curriculum)
    db_session.flush()
    key_stage = KeyStage(curriculum_id=curriculum.id, code="EYFS", name="Early Years", sort_order=0)
    db_session.add(key_stage)
    db_session.flush()
    year_group = YearGroup(key_stage_id=key_stage.id, code="RECEPTION", name="Reception", sort_order=0)
    subject = Subject(curriculum_id=curriculum.id, code="ENG", name="English")
    db_session.add_all([year_group, subject])
    db_session.flush()
    pos = ProgrammeOfStudy(subject_id=subject.id, year_group_id=year_group.id)
    db_session.add(pos)
    db_session.flush()

    topics = []
    for i in range(count):
        topic = CurriculumTopic(programme_of_study_id=pos.id, title=f"Topic {i + 1}", sort_order=i)
        db_session.add(topic)
        topics.append(topic)
    db_session.commit()
    return {"subject": subject, "year_group": year_group, "topics": topics}


def test_new_teacher_gets_the_first_topic_in_sequence(client, db_session):
    seed = _seed_sequence(db_session)
    account = register_teacher(client)
    user = db_session.query(User).filter_by(email=account["email"]).first()

    topic, is_new = suggest_topic_progression(db_session, user, seed["subject"].id, seed["year_group"].id)
    assert is_new is True
    assert topic.id == seed["topics"][0].id


def test_existing_teacher_gets_the_next_uncovered_topic(client, db_session):
    seed = _seed_sequence(db_session)
    account = register_teacher(client)
    user = db_session.query(User).filter_by(email=account["email"]).first()

    # Teacher has already covered the first topic.
    plan = LessonPlan(
        owner_user_id=user.id,
        subject_id=seed["subject"].id,
        year_group_id=seed["year_group"].id,
        curriculum_topic_id=seed["topics"][0].id,
        topic_title=seed["topics"][0].title,
        duration_minutes=30,
        ability_level=AbilityLevel.MIXED,
    )
    db_session.add(plan)
    db_session.commit()

    topic, is_new = suggest_topic_progression(db_session, user, seed["subject"].id, seed["year_group"].id)
    assert is_new is False
    assert topic.id == seed["topics"][1].id


def test_progression_cycles_back_once_every_topic_is_covered(client, db_session):
    seed = _seed_sequence(db_session, count=2)
    account = register_teacher(client)
    user = db_session.query(User).filter_by(email=account["email"]).first()
    for topic in seed["topics"]:
        db_session.add(
            LessonPlan(
                owner_user_id=user.id,
                subject_id=seed["subject"].id,
                year_group_id=seed["year_group"].id,
                curriculum_topic_id=topic.id,
                topic_title=topic.title,
                duration_minutes=30,
                ability_level=AbilityLevel.MIXED,
            )
        )
    db_session.commit()

    topic, is_new = suggest_topic_progression(db_session, user, seed["subject"].id, seed["year_group"].id)
    assert is_new is False
    assert topic.id == seed["topics"][0].id  # cycled back, never stuck with nothing


def test_list_topic_progress_flags_covered_and_recommended(client, db_session):
    seed = _seed_sequence(db_session)
    account = register_teacher(client)
    user = db_session.query(User).filter_by(email=account["email"]).first()
    db_session.add(
        LessonPlan(
            owner_user_id=user.id,
            subject_id=seed["subject"].id,
            year_group_id=seed["year_group"].id,
            curriculum_topic_id=seed["topics"][0].id,
            topic_title=seed["topics"][0].title,
            duration_minutes=30,
            ability_level=AbilityLevel.MIXED,
        )
    )
    db_session.commit()

    entries = list_topic_progress(db_session, user, seed["subject"].id, seed["year_group"].id)
    assert len(entries) == 3
    assert entries[0]["covered"] is True
    assert entries[0]["is_recommended"] is False
    assert entries[1]["covered"] is False
    assert entries[1]["is_recommended"] is True


def test_topic_suggestions_endpoint(client, db_session):
    seed = _seed_sequence(db_session)
    account = register_teacher(client)

    res = client.get(
        "/api/v1/lesson-plans/topic-suggestions",
        params={"subject_id": str(seed["subject"].id), "year_group_id": str(seed["year_group"].id)},
        headers=auth_headers(account),
    )
    assert res.status_code == 200, res.text
    assert len(res.json()) == 3
    assert res.json()[0]["is_recommended"] is True


def test_quick_generate_with_no_topic_uses_progression(client, db_session):
    seed = _seed_sequence(db_session)
    account = register_teacher(client)

    intent = QuickLessonIntent(subject_name="English", year_group_or_key_stage="Reception", topic=None, relative_date_phrase="tomorrow")
    override_ai_provider(intent, SAMPLE_CONTENT)
    res = client.post(
        "/api/v1/lesson-plans/quick-generate", json={"text": "Make me a lesson plan for tomorrow."}, headers=auth_headers(account)
    )
    clear_ai_override()

    assert res.status_code == 201, res.text
    assert res.json()["topic_title"] == seed["topics"][0].title


def test_quick_generate_continue_phrasing_picks_next_topic(client, db_session):
    seed = _seed_sequence(db_session)
    account = register_teacher(client)
    headers = auth_headers(account)

    # First lesson (no topic named) -- covers topic 1.
    intent1 = QuickLessonIntent(subject_name="English", year_group_or_key_stage="Reception", topic=None)
    override_ai_provider(intent1, SAMPLE_CONTENT)
    first = client.post("/api/v1/lesson-plans/quick-generate", json={"text": "Make me a lesson for tomorrow."}, headers=headers)
    clear_ai_override()
    assert first.status_code == 201
    assert first.json()["topic_title"] == seed["topics"][0].title

    # "Continue" phrasing -- the AI extractor is expected to leave topic
    # null for this, same as any other no-topic request.
    intent2 = QuickLessonIntent(subject_name="English", year_group_or_key_stage="Reception", topic=None)
    override_ai_provider(intent2, SAMPLE_CONTENT)
    second = client.post("/api/v1/lesson-plans/quick-generate", json={"text": "Continue my next English lesson."}, headers=headers)
    clear_ai_override()
    assert second.status_code == 201
    assert second.json()["topic_title"] == seed["topics"][1].title
