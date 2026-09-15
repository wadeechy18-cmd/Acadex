from datetime import date, timedelta

from app.schemas.quick_lesson import QuickLessonIntent
from tests.conftest import auth_headers, register_teacher
from tests.test_lesson_plans import SAMPLE_CONTENT, _seed_curriculum, clear_ai_override, override_ai_provider


def test_quick_generate_resolves_tomorrow_and_matches_subject_and_topic(client, db_session):
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)

    intent = QuickLessonIntent(subject_name="Mathematics", year_group_or_key_stage="Year 2", topic="Fractions", relative_date_phrase="tomorrow")
    override_ai_provider(intent, SAMPLE_CONTENT)
    res = client.post(
        "/api/v1/lesson-plans/quick-generate",
        json={"text": "Make me a lesson plan for tomorrow on fractions."},
        headers=auth_headers(teacher),
    )
    clear_ai_override()

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["topic_title"] == "Fractions"
    assert body["subject_id"] == str(seed["subject"].id)
    assert body["year_group_id"] == str(seed["year_group"].id)
    assert body["scheduled_date"] == str(date.today() + timedelta(days=1))
    assert body["current_version"]["worksheet"] is not None
    assert body["current_version"]["homework_task"] is not None


def test_quick_generate_falls_back_to_last_plans_subject_and_year_group(client, db_session):
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    headers = auth_headers(teacher)

    # An explicit plan first, to seed a "last used" subject/year group.
    override_ai_provider(SAMPLE_CONTENT)
    first = client.post(
        "/api/v1/lesson-plans/generate",
        json={
            "subject_id": str(seed["subject"].id),
            "year_group_id": str(seed["year_group"].id),
            "curriculum_topic_id": str(seed["topic"].id),
            "duration_minutes": 30,
            "ability_level": "mixed",
        },
        headers=headers,
    )
    clear_ai_override()
    assert first.status_code == 201

    intent = QuickLessonIntent(topic="a new topic about shapes")
    override_ai_provider(intent, SAMPLE_CONTENT)
    res = client.post("/api/v1/lesson-plans/quick-generate", json={"text": "Make me a lesson for tomorrow."}, headers=headers)
    clear_ai_override()

    assert res.status_code == 201, res.text
    assert res.json()["subject_id"] == str(seed["subject"].id)
    assert res.json()["year_group_id"] == str(seed["year_group"].id)


def test_quick_generate_returns_422_when_subject_and_year_group_cannot_be_resolved(client, db_session):
    _seed_curriculum(db_session)
    teacher = register_teacher(client)

    intent = QuickLessonIntent(topic="something")
    override_ai_provider(intent)
    res = client.post(
        "/api/v1/lesson-plans/quick-generate", json={"text": "Teach me something."}, headers=auth_headers(teacher)
    )
    clear_ai_override()
    assert res.status_code == 422


def test_quick_generate_without_ai_configured_returns_503(client, db_session):
    _seed_curriculum(db_session)
    clear_ai_override()
    teacher = register_teacher(client)
    res = client.post(
        "/api/v1/lesson-plans/quick-generate", json={"text": "Make me a lesson for tomorrow."}, headers=auth_headers(teacher)
    )
    assert res.status_code == 503
