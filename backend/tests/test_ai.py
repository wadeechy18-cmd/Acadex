"""Every test here uses a FakeAIProvider -- never the real Anthropic API.
Automated tests must not spend real money or depend on network access, and
must be deterministic; app.dependency_overrides is the same mechanism
conftest.py already uses to swap the real DB session for a test one.
"""

import uuid

from pydantic import BaseModel

from app.ai.provider import AIGenerationResult, get_ai_provider
from app.main import app
from app.schemas.lesson_plan import LessonPlanContent, LessonSection
from tests.conftest import auth_headers
from tests.test_lesson_plans import create_lesson_plan, create_school_class
from tests.test_organizations import register_teacher
from tests.test_resources import upload


class FakeAIProvider:
    def __init__(self, content: LessonPlanContent | None = None, input_tokens: int = 500, output_tokens: int = 300):
        self.content = content or LessonPlanContent(
            learning_objectives=["AI-suggested objective"],
            sections=[LessonSection(id="ai-1", type="starter", title="AI Starter", duration_minutes=50, body=[])],
        )
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.calls: list[dict] = []

    def generate_structured(self, *, system: str, prompt: str, schema: type[BaseModel]) -> AIGenerationResult:
        self.calls.append({"system": system, "prompt": prompt, "schema": schema})
        return AIGenerationResult(
            parsed=self.content, input_tokens=self.input_tokens, output_tokens=self.output_tokens, model="claude-opus-5"
        )


def override_ai_provider(fake: FakeAIProvider):
    app.dependency_overrides[get_ai_provider] = lambda: fake


def clear_ai_override():
    app.dependency_overrides.pop(get_ai_provider, None)


def test_ai_enhance_returns_503_when_not_configured(client):
    """No override -> the real factory runs, sees no API key in this test
    environment, and returns None -- the endpoint must not crash.
    """
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    res = client.post(f"/api/v1/lesson-plans/{plan['id']}/ai-enhance", json={}, headers=auth_headers(owner))
    assert res.status_code == 503


def test_ai_enhance_with_stub_provider_returns_structured_content_and_records_usage(client, db_session):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    fake = FakeAIProvider()
    override_ai_provider(fake)
    try:
        res = client.post(
            f"/api/v1/lesson-plans/{plan['id']}/ai-enhance",
            json={"instructions": "Make the starter more engaging"},
            headers=auth_headers(owner),
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["learning_objectives"] == ["AI-suggested objective"]
        assert len(fake.calls) == 1  # exactly one structured call, never more
        assert "Make the starter more engaging" in fake.calls[0]["prompt"]

        from app.models.usage_record import UsageRecord

        records = db_session.query(UsageRecord).all()
        assert len(records) == 1
        assert records[0].input_tokens == 500
        assert records[0].output_tokens == 300
        assert records[0].estimated_cost_cents > 0
    finally:
        clear_ai_override()


def test_ai_enhance_does_not_persist_a_new_lesson_plan_version(client):
    """The AI's suggestion is a preview -- only an explicit Save (the existing
    Phase 3 endpoint) creates a new version.
    """
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    fake = FakeAIProvider()
    override_ai_provider(fake)
    try:
        client.post(f"/api/v1/lesson-plans/{plan['id']}/ai-enhance", json={}, headers=auth_headers(owner))
        detail = client.get(f"/api/v1/lesson-plans/{plan['id']}", headers=auth_headers(owner)).json()
        assert detail["latest_version_number"] == 1  # unchanged
        assert detail["content"]["learning_objectives"] == []  # AI suggestion was never saved
    finally:
        clear_ai_override()


def test_ai_enhance_blocks_safeguarding_sensitive_topics_without_calling_the_model(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id, title="Understanding grooming risks", topic="Online safety and grooming")

    fake = FakeAIProvider()
    override_ai_provider(fake)
    try:
        res = client.post(f"/api/v1/lesson-plans/{plan['id']}/ai-enhance", json={}, headers=auth_headers(owner))
        assert res.status_code == 422
        assert "DSL procedure" in res.json()["detail"]
        assert len(fake.calls) == 0  # never reached the model
    finally:
        clear_ai_override()


def test_ai_enhance_requires_ownership(client):
    owner, school_id, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    teacher = register_teacher(client)
    client.post(f"/api/v1/organizations/{school_id}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(owner))

    fake = FakeAIProvider()
    override_ai_provider(fake)
    try:
        res = client.post(f"/api/v1/lesson-plans/{plan['id']}/ai-enhance", json={}, headers=auth_headers(teacher))
        assert res.status_code == 403
        assert len(fake.calls) == 0
    finally:
        clear_ai_override()


def test_ai_enhance_includes_selected_resource_text_in_the_prompt(client):
    owner, org_id, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    resource_res = upload(client, owner, org_id, b"KS4 Chemistry: atomic structure specification excerpt.", "spec.txt", "text/plain")
    resource_id = resource_res.json()["id"]

    fake = FakeAIProvider()
    override_ai_provider(fake)
    try:
        res = client.post(
            f"/api/v1/lesson-plans/{plan['id']}/ai-enhance",
            json={"resource_ids": [resource_id]},
            headers=auth_headers(owner),
        )
        assert res.status_code == 200
        assert "atomic structure specification excerpt" in fake.calls[0]["prompt"]
    finally:
        clear_ai_override()


def test_ai_enhance_rejects_a_resource_the_caller_cannot_see(client):
    owner, org_id, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    teacher = register_teacher(client)
    client.post(f"/api/v1/organizations/{org_id}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(owner))
    private_res = upload(client, teacher, org_id, b"teacher private notes", "private.txt", "text/plain", visibility="private")
    private_id = private_res.json()["id"]

    fake = FakeAIProvider()
    override_ai_provider(fake)
    try:
        res = client.post(
            f"/api/v1/lesson-plans/{plan['id']}/ai-enhance",
            json={"resource_ids": [private_id]},
            headers=auth_headers(owner),  # owner did not upload it and it's private to the teacher
        )
        assert res.status_code == 404
        assert len(fake.calls) == 0
    finally:
        clear_ai_override()


def test_usage_summary_aggregates_and_requires_admin(client):
    owner, org_id, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    teacher = register_teacher(client)
    client.post(f"/api/v1/organizations/{org_id}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(owner))

    fake = FakeAIProvider(input_tokens=1000, output_tokens=500)
    override_ai_provider(fake)
    try:
        client.post(f"/api/v1/lesson-plans/{plan['id']}/ai-enhance", json={}, headers=auth_headers(owner))
        client.post(f"/api/v1/lesson-plans/{plan['id']}/ai-enhance", json={}, headers=auth_headers(owner))

        summary = client.get(f"/api/v1/organizations/{org_id}/usage", headers=auth_headers(owner)).json()
        assert summary["total_requests"] == 2
        assert summary["total_input_tokens"] == 2000
        assert summary["total_output_tokens"] == 1000
        assert summary["total_estimated_cost_cents"] > 0

        forbidden = client.get(f"/api/v1/organizations/{org_id}/usage", headers=auth_headers(teacher))
        assert forbidden.status_code == 403
    finally:
        clear_ai_override()
