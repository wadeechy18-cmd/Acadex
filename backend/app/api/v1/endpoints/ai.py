import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.provider import AIProvider, get_ai_provider
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai import AIEnhanceRequest, UsageSummaryResponse
from app.schemas.lesson_plan import LessonPlanContent
from app.services import ai_service

router = APIRouter(tags=["ai"])


@router.post("/lesson-plans/{lesson_plan_id}/ai-enhance", response_model=LessonPlanContent)
def ai_enhance_lesson_plan(
    lesson_plan_id: uuid.UUID,
    payload: AIEnhanceRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    provider: AIProvider | None = Depends(get_ai_provider),
) -> LessonPlanContent:
    if provider is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI features are not configured for this deployment.")
    return ai_service.enhance_lesson_plan(
        db, user, lesson_plan_id, instructions=payload.instructions, resource_ids=payload.resource_ids, provider=provider
    )


@router.get("/organizations/{organization_id}/usage", response_model=UsageSummaryResponse)
def get_usage_summary(
    organization_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> UsageSummaryResponse:
    return ai_service.get_usage_summary(db, user, organization_id)
