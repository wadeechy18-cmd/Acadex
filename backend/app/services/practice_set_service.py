"""Shared CRUD + AI-generation logic for Worksheet and Homework -- both are
the same PracticeSetContent shape hung off a lesson plan, differing only in
their table and (for Homework) a due_date column, so one generic service
avoids maintaining two near-identical copies of the same permission and
persistence logic.
"""

import uuid
from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai.pricing import estimate_cost_cents
from app.ai.provider import AIProvider
from app.models.usage_record import UsageRecord
from app.models.user import User
from app.planning.validator import is_safeguarding_sensitive
from app.schemas.worksheet import PracticeSetContent
from app.services import resource_service
from app.services.lesson_plan_service import assert_can_manage_lesson_plan, get_lesson_plan

ModelT = TypeVar("ModelT")

_SYSTEM_PROMPT_TEMPLATE = (
    "You are helping a UK teacher create a {kind} for their class, linked to a "
    "specific lesson. Return structured JSON matching the given schema: brief "
    "instructions for the student, then a flat list of items, each with a "
    "short free-text group label (e.g. Retrieval/Core/Challenge), a prompt, a "
    "mark value, and a model answer. Keep language and difficulty age- and "
    "stage-appropriate for the class described below. If curriculum source "
    "material is provided, treat it as the authoritative source of truth -- "
    "never contradict it or invent requirements beyond it. Never include "
    "safeguarding-sensitive content, and never make any claim about a "
    "specific student's abilities, diagnoses, or needs."
)


def list_for_lesson_plan(db: Session, user: User, model_cls: type[ModelT], lesson_plan_id: uuid.UUID) -> list[ModelT]:
    get_lesson_plan(db, user, lesson_plan_id)  # view access -- membership check only
    return (
        db.query(model_cls)
        .filter_by(lesson_plan_id=lesson_plan_id)
        .order_by(model_cls.created_at.desc())
        .all()
    )


def get_one(db: Session, user: User, model_cls: type[ModelT], item_id: uuid.UUID) -> ModelT:
    item = db.get(model_cls, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model_cls.__name__} not found.")
    get_lesson_plan(db, user, item.lesson_plan_id)  # raises 403 if not an org member
    return item


def assert_can_manage(db: Session, user: User, model_cls: type[ModelT], item_id: uuid.UUID) -> ModelT:
    item = get_one(db, user, model_cls, item_id)
    assert_can_manage_lesson_plan(db, user, item.lesson_plan_id)  # only the owning teacher may edit
    return item


def create(
    db: Session,
    user: User,
    model_cls: type[ModelT],
    lesson_plan_id: uuid.UUID,
    *,
    title: str,
    content: PracticeSetContent,
    extra_fields: dict | None = None,
) -> ModelT:
    lesson_plan = assert_can_manage_lesson_plan(db, user, lesson_plan_id)
    item = model_cls(
        lesson_plan_id=lesson_plan.id,
        title=title,
        content=content.model_dump(mode="json"),
        **(extra_fields or {}),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update(db: Session, user: User, model_cls: type[ModelT], item_id: uuid.UUID, *, updates: dict) -> ModelT:
    """`updates` comes from an Update schema's `.model_dump(exclude_unset=True)`
    -- Pydantic has already recursed `content` into a plain JSON-safe dict, so
    it can be assigned to the JSON column as-is.
    """
    item = assert_can_manage(db, user, model_cls, item_id)
    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete(db: Session, user: User, model_cls: type[ModelT], item_id: uuid.UUID) -> None:
    item = assert_can_manage(db, user, model_cls, item_id)
    db.delete(item)
    db.commit()


def generate_content_with_ai(
    db: Session,
    user: User,
    lesson_plan_id: uuid.UUID,
    *,
    kind: str,
    instructions: str | None,
    item_count: int,
    resource_ids: list[uuid.UUID],
    provider: AIProvider,
) -> PracticeSetContent:
    """Preview-only: returns generated content for the teacher to review and
    edit before saving via create()/update() -- it never persists a
    Worksheet/Homework row itself.
    """
    lesson_plan = assert_can_manage_lesson_plan(db, user, lesson_plan_id)

    if is_safeguarding_sensitive(lesson_plan.topic, lesson_plan.title):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"This lesson is flagged as safeguarding-sensitive and can't be sent for AI {kind} generation. "
            "Create it manually and follow your school's safeguarding/DSL procedure.",
        )

    prompt_parts = [
        f"Lesson topic: {lesson_plan.topic}. Create approximately {item_count} items.",
    ]
    if instructions:
        prompt_parts.append(f"Teacher's instructions: {instructions}")

    resource_context = resource_service.build_context_excerpt(db, user, resource_ids)
    if resource_context:
        prompt_parts.append(f"Authoritative curriculum source material:\n{resource_context}")

    result = provider.generate_structured(
        system=_SYSTEM_PROMPT_TEMPLATE.format(kind=kind),
        prompt="\n\n".join(prompt_parts),
        schema=PracticeSetContent,
    )

    db.add(
        UsageRecord(
            organization_id=lesson_plan.organization_id,
            user_id=user.id,
            provider="anthropic",
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            estimated_cost_cents=estimate_cost_cents(result.model, result.input_tokens, result.output_tokens),
        )
    )
    db.commit()

    return result.parsed
