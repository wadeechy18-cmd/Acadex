import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai.pricing import estimate_cost_cents
from app.ai.provider import AIProvider
from app.models.organization import OrganizationRole
from app.models.planner_class import TeachingClass
from app.models.usage_record import UsageRecord
from app.models.user import User
from app.planning.validator import is_safeguarding_sensitive
from app.schemas.ai import UsageSummaryResponse
from app.schemas.lesson_plan import LessonPlanContent
from app.services import resource_service
from app.services.lesson_plan_service import assert_can_manage_lesson_plan, get_latest_version
from app.services.organization_service import assert_org_member

# Keeps a single request from ballooning the prompt (and the bill) if a
# teacher selects several large resources -- excerpts, not full documents.
_MAX_RESOURCE_CONTEXT_CHARS = 6000

_SYSTEM_PROMPT = (
    "You are helping a UK teacher refine a lesson plan for their class. Return "
    "a complete, improved version of the lesson plan content as structured "
    "JSON matching the given schema -- refine what's there, don't discard it "
    "without reason. Keep language and difficulty age-appropriate for the "
    "stated year group, and consistent with the stated qualification and exam "
    "board where given. If curriculum source material is provided below, "
    "treat it as the authoritative source of truth -- never contradict it or "
    "invent requirements beyond it. Section durations must sum to exactly the "
    "lesson's total duration. Never add or imply safeguarding-sensitive "
    "content, and never make any claim about a specific student's abilities, "
    "diagnoses, or needs."
)


def _build_resource_context(db: Session, user: User, resource_ids: list[uuid.UUID]) -> str:
    parts = []
    for resource_id in resource_ids:
        resource = resource_service.get_resource(db, user, resource_id)  # enforces visibility -- 404s, never substitutes
        chunks = resource_service.list_chunks(db, user, resource_id)
        parts.append(f"--- {resource.file_name} ---\n" + "\n".join(c.text for c in chunks))
    return "\n\n".join(parts)[:_MAX_RESOURCE_CONTEXT_CHARS]


def enhance_lesson_plan(
    db: Session,
    user: User,
    lesson_plan_id: uuid.UUID,
    *,
    instructions: str | None,
    resource_ids: list[uuid.UUID],
    provider: AIProvider,
) -> LessonPlanContent:
    lesson_plan = assert_can_manage_lesson_plan(db, user, lesson_plan_id)

    if is_safeguarding_sensitive(lesson_plan.topic, lesson_plan.title):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "This lesson is flagged as safeguarding-sensitive and can't be sent for AI enhancement. "
            "Edit it manually and follow your school's safeguarding/DSL procedure.",
        )

    latest = get_latest_version(db, lesson_plan.id)
    current_content = LessonPlanContent.model_validate(latest.content)
    teaching_class = db.get(TeachingClass, lesson_plan.class_id)

    prompt_parts = [
        f"Class: {teaching_class.subject_name}, {teaching_class.year_group.value}, "
        f"{teaching_class.qualification or 'no qualification specified'}"
        + (f", {teaching_class.exam_board_name}" if teaching_class.exam_board_name else "") + ".",
        f"Lesson topic: {lesson_plan.topic}. Total duration: {lesson_plan.duration_minutes} minutes.",
        f"Current lesson plan content (JSON): {current_content.model_dump_json()}",
    ]
    if instructions:
        prompt_parts.append(f"Teacher's instructions: {instructions}")

    resource_context = _build_resource_context(db, user, resource_ids)
    if resource_context:
        prompt_parts.append(f"Authoritative curriculum source material:\n{resource_context}")

    result = provider.generate_structured(
        system=_SYSTEM_PROMPT, prompt="\n\n".join(prompt_parts), schema=LessonPlanContent
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


def get_usage_summary(db: Session, user: User, organization_id: uuid.UUID) -> UsageSummaryResponse:
    # Cost visibility is admin/owner-only -- a plain teacher member doesn't
    # need to see the whole workspace's AI spend.
    assert_org_member(db, user, organization_id, min_role=OrganizationRole.ADMIN)

    records = db.query(UsageRecord).filter_by(organization_id=organization_id).all()
    return UsageSummaryResponse(
        total_requests=len(records),
        total_input_tokens=sum(r.input_tokens for r in records),
        total_output_tokens=sum(r.output_tokens for r in records),
        total_estimated_cost_cents=sum(r.estimated_cost_cents for r in records),
    )
