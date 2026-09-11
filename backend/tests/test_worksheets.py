"""Phase 7: worksheets and homework. Both share one PracticeSetContent shape
(see app/services/practice_set_service.py) so most coverage lives here for
worksheets, with homework tests focused on what's actually different
(due_date) plus one end-to-end pass per route to prove the wiring works.
"""

from tests.conftest import auth_headers
from tests.test_ai import FakeAIProvider, clear_ai_override, override_ai_provider
from tests.test_lesson_plans import create_lesson_plan, create_school_class
from tests.test_organizations import register_teacher


def _practice_content(n: int = 2) -> dict:
    return {
        "instructions": "Answer in full sentences.",
        "items": [
            {"id": f"q{i}", "group": "Core", "prompt": f"Question {i}?", "marks": 5, "answer": f"Answer {i}"}
            for i in range(1, n + 1)
        ],
    }


def create_worksheet(client, owner, plan_id, **overrides):
    payload = {"title": "Practice Sheet", "content": _practice_content(), **overrides}
    res = client.post(f"/api/v1/lesson-plans/{plan_id}/worksheets", json=payload, headers=auth_headers(owner))
    assert res.status_code == 201, res.text
    return res.json()


def test_create_worksheet_computes_total_marks_and_estimated_minutes(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    worksheet = create_worksheet(client, owner, plan["id"])
    assert worksheet["total_marks"] == 10  # two items worth 5 marks each
    assert worksheet["estimated_minutes"] == 15  # 10 marks * 1.5 minutes/mark


def test_list_worksheets_for_lesson_plan(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)
    create_worksheet(client, owner, plan["id"], title="Sheet A")
    create_worksheet(client, owner, plan["id"], title="Sheet B")

    listed = client.get(f"/api/v1/lesson-plans/{plan['id']}/worksheets", headers=auth_headers(owner)).json()
    assert {w["title"] for w in listed} == {"Sheet A", "Sheet B"}


def test_answer_key_is_derived_from_content_not_a_separate_store(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)
    worksheet = create_worksheet(client, owner, plan["id"])

    key = client.get(f"/api/v1/worksheets/{worksheet['id']}/answer-key", headers=auth_headers(owner)).json()
    assert key["total_marks"] == 10
    assert [e["answer"] for e in key["entries"]] == ["Answer 1", "Answer 2"]

    # Editing content changes the derived key on the next read -- nothing to
    # keep in sync manually.
    new_content = _practice_content(n=1)
    client.patch(
        f"/api/v1/worksheets/{worksheet['id']}", json={"content": new_content}, headers=auth_headers(owner)
    )
    key_after = client.get(f"/api/v1/worksheets/{worksheet['id']}/answer-key", headers=auth_headers(owner)).json()
    assert key_after["total_marks"] == 5
    assert len(key_after["entries"]) == 1


def test_delete_worksheet(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)
    worksheet = create_worksheet(client, owner, plan["id"])

    res = client.delete(f"/api/v1/worksheets/{worksheet['id']}", headers=auth_headers(owner))
    assert res.status_code == 204
    assert client.get(f"/api/v1/worksheets/{worksheet['id']}", headers=auth_headers(owner)).status_code == 404


def test_org_member_can_view_but_not_edit_another_teachers_worksheet(client):
    owner, org_id, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)
    worksheet = create_worksheet(client, owner, plan["id"])

    colleague = register_teacher(client)
    client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": colleague["email"], "role": "teacher"},
        headers=auth_headers(owner),
    )

    view = client.get(f"/api/v1/worksheets/{worksheet['id']}", headers=auth_headers(colleague))
    assert view.status_code == 200

    edit = client.patch(
        f"/api/v1/worksheets/{worksheet['id']}", json={"title": "Hijacked"}, headers=auth_headers(colleague)
    )
    assert edit.status_code == 403

    delete = client.delete(f"/api/v1/worksheets/{worksheet['id']}", headers=auth_headers(colleague))
    assert delete.status_code == 403


def test_non_member_cannot_view_worksheet(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)
    worksheet = create_worksheet(client, owner, plan["id"])

    outsider = register_teacher(client)
    res = client.get(f"/api/v1/worksheets/{worksheet['id']}", headers=auth_headers(outsider))
    assert res.status_code == 403


def test_worksheet_ai_generate_returns_503_when_not_configured(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    res = client.post(f"/api/v1/lesson-plans/{plan['id']}/worksheets/ai-generate", json={}, headers=auth_headers(owner))
    assert res.status_code == 503


def test_worksheet_ai_generate_with_stub_provider_records_usage(client, db_session):
    from app.schemas.worksheet import PracticeSetContent

    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    fake = FakeAIProvider(
        content=PracticeSetContent.model_validate(_practice_content(n=3)), input_tokens=200, output_tokens=100
    )
    override_ai_provider(fake)
    try:
        res = client.post(
            f"/api/v1/lesson-plans/{plan['id']}/worksheets/ai-generate",
            json={"instructions": "Focus on definitions", "item_count": 3},
            headers=auth_headers(owner),
        )
        assert res.status_code == 200, res.text
        assert len(res.json()["items"]) == 3
        assert len(fake.calls) == 1
        assert "Focus on definitions" in fake.calls[0]["prompt"]

        from app.models.usage_record import UsageRecord

        assert db_session.query(UsageRecord).count() == 1
    finally:
        clear_ai_override()


def test_worksheet_ai_generate_blocks_safeguarding_sensitive_topics(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(
        client, owner, class_id, title="Understanding grooming risks", topic="Online safety and grooming"
    )

    fake = FakeAIProvider()
    override_ai_provider(fake)
    try:
        res = client.post(f"/api/v1/lesson-plans/{plan['id']}/worksheets/ai-generate", json={}, headers=auth_headers(owner))
        assert res.status_code == 422
        assert len(fake.calls) == 0
    finally:
        clear_ai_override()


# --- Homework: only what's different (due_date) plus one end-to-end pass. ---


def create_homework(client, owner, plan_id, **overrides):
    payload = {"title": "Homework 1", "content": _practice_content(), "due_date": "2026-09-20", **overrides}
    res = client.post(f"/api/v1/lesson-plans/{plan_id}/homework", json=payload, headers=auth_headers(owner))
    assert res.status_code == 201, res.text
    return res.json()


def test_create_homework_with_due_date_and_answer_key(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    homework = create_homework(client, owner, plan["id"])
    assert homework["due_date"] == "2026-09-20"
    assert homework["total_marks"] == 10

    key = client.get(f"/api/v1/homework/{homework['id']}/answer-key", headers=auth_headers(owner)).json()
    assert key["total_marks"] == 10


def test_homework_due_date_can_be_cleared(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)
    homework = create_homework(client, owner, plan["id"])

    res = client.patch(f"/api/v1/homework/{homework['id']}", json={"due_date": None}, headers=auth_headers(owner))
    assert res.status_code == 200
    assert res.json()["due_date"] is None


def test_homework_ownership_enforced_same_as_worksheet(client):
    owner, org_id, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)
    homework = create_homework(client, owner, plan["id"])

    colleague = register_teacher(client)
    client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": colleague["email"], "role": "teacher"},
        headers=auth_headers(owner),
    )
    edit = client.patch(f"/api/v1/homework/{homework['id']}", json={"title": "Hijacked"}, headers=auth_headers(colleague))
    assert edit.status_code == 403


def test_homework_ai_generate_returns_503_when_not_configured(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    res = client.post(f"/api/v1/lesson-plans/{plan['id']}/homework/ai-generate", json={}, headers=auth_headers(owner))
    assert res.status_code == 503


def test_worksheets_and_homework_are_deleted_when_lesson_plan_is_deleted(client, db_session):
    """ondelete=CASCADE on lesson_plan_id -- verified against the real
    database, not assumed from the model definition.
    """
    from app.models.worksheet import Homework, Worksheet

    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)
    worksheet = create_worksheet(client, owner, plan["id"])
    homework = create_homework(client, owner, plan["id"])

    res = client.delete(f"/api/v1/lesson-plans/{plan['id']}", headers=auth_headers(owner))
    assert res.status_code == 204

    db_session.expire_all()
    import uuid as uuid_module

    assert db_session.get(Worksheet, uuid_module.UUID(worksheet["id"])) is None
    assert db_session.get(Homework, uuid_module.UUID(homework["id"])) is None
