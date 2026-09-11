import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.lesson_plan import LessonPlan, LessonPlanVersion
from app.models.user import User
from app.planning.validator import LessonPlanQualityReport
from app.schemas.lesson_plan import (
    LessonPlanContent,
    LessonPlanCreate,
    LessonPlanDetail,
    LessonPlanResponse,
    LessonPlanUpdate,
    LessonPlanVersionSummary,
    QualityCheckRequest,
    SaveContentRequest,
)
from app.services import export_service, lesson_plan_service

router = APIRouter(tags=["lesson-plans"])


def _to_response(db: Session, lesson_plan: LessonPlan) -> LessonPlanResponse:
    return LessonPlanResponse(
        id=lesson_plan.id,
        organization_id=lesson_plan.organization_id,
        class_id=lesson_plan.class_id,
        teacher_user_id=lesson_plan.teacher_user_id,
        title=lesson_plan.title,
        topic=lesson_plan.topic,
        duration_minutes=lesson_plan.duration_minutes,
        template_type=lesson_plan.template_type,
        status=lesson_plan.status,
        created_at=lesson_plan.created_at,
        updated_at=lesson_plan.updated_at,
        latest_version_number=lesson_plan_service.get_latest_version_number(db, lesson_plan.id),
    )


@router.post("/classes/{class_id}/lesson-plans", response_model=LessonPlanResponse, status_code=status.HTTP_201_CREATED)
def create_lesson_plan(
    class_id: uuid.UUID,
    payload: LessonPlanCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LessonPlanResponse:
    lesson_plan = lesson_plan_service.create_lesson_plan(db, user, class_id, payload)
    return _to_response(db, lesson_plan)


@router.get("/classes/{class_id}/lesson-plans", response_model=list[LessonPlanResponse])
def list_lesson_plans(
    class_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[LessonPlanResponse]:
    plans = lesson_plan_service.list_lesson_plans(db, user, class_id)
    return [_to_response(db, p) for p in plans]


@router.get("/lesson-plans/{lesson_plan_id}", response_model=LessonPlanDetail)
def get_lesson_plan(
    lesson_plan_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> LessonPlanDetail:
    lesson_plan = lesson_plan_service.get_lesson_plan(db, user, lesson_plan_id)
    latest = lesson_plan_service.get_latest_version(db, lesson_plan_id)
    return LessonPlanDetail(
        id=lesson_plan.id,
        organization_id=lesson_plan.organization_id,
        class_id=lesson_plan.class_id,
        teacher_user_id=lesson_plan.teacher_user_id,
        title=lesson_plan.title,
        topic=lesson_plan.topic,
        duration_minutes=lesson_plan.duration_minutes,
        template_type=lesson_plan.template_type,
        status=lesson_plan.status,
        created_at=lesson_plan.created_at,
        updated_at=lesson_plan.updated_at,
        latest_version_number=latest.version_number,
        content=LessonPlanContent.model_validate(latest.content),
    )


@router.get("/lesson-plans/{lesson_plan_id}/quality-check", response_model=LessonPlanQualityReport)
def quality_check(
    lesson_plan_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> LessonPlanQualityReport:
    return lesson_plan_service.get_quality_report(db, user, lesson_plan_id)


@router.post("/lesson-plans/{lesson_plan_id}/quality-check", response_model=LessonPlanQualityReport)
def quality_check_draft(
    lesson_plan_id: uuid.UUID,
    payload: QualityCheckRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LessonPlanQualityReport:
    return lesson_plan_service.get_draft_quality_report(
        db, user, lesson_plan_id,
        title=payload.title, topic=payload.topic, duration_minutes=payload.duration_minutes,
        template_type=payload.template_type, content=payload.content,
    )


@router.patch("/lesson-plans/{lesson_plan_id}", response_model=LessonPlanResponse)
def update_lesson_plan(
    lesson_plan_id: uuid.UUID,
    payload: LessonPlanUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LessonPlanResponse:
    lesson_plan = lesson_plan_service.update_lesson_plan(db, user, lesson_plan_id, payload)
    return _to_response(db, lesson_plan)


@router.put("/lesson-plans/{lesson_plan_id}/content", response_model=LessonPlanVersionSummary)
def save_content(
    lesson_plan_id: uuid.UUID,
    payload: SaveContentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LessonPlanVersion:
    return lesson_plan_service.save_content(db, user, lesson_plan_id, payload.content)


@router.get("/lesson-plans/{lesson_plan_id}/versions", response_model=list[LessonPlanVersionSummary])
def list_versions(
    lesson_plan_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[LessonPlanVersion]:
    return lesson_plan_service.list_versions(db, user, lesson_plan_id)


@router.post("/lesson-plans/{lesson_plan_id}/versions/{version_id}/restore", response_model=LessonPlanVersionSummary)
def restore_version(
    lesson_plan_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LessonPlanVersion:
    return lesson_plan_service.restore_version(db, user, lesson_plan_id, version_id)


@router.post("/lesson-plans/{lesson_plan_id}/duplicate", response_model=LessonPlanResponse, status_code=status.HTTP_201_CREATED)
def duplicate_lesson_plan(
    lesson_plan_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> LessonPlanResponse:
    copy = lesson_plan_service.duplicate_lesson_plan(db, user, lesson_plan_id)
    return _to_response(db, copy)


@router.delete("/lesson-plans/{lesson_plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson_plan(
    lesson_plan_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    lesson_plan_service.delete_lesson_plan(db, user, lesson_plan_id)


@router.get("/lesson-plans/{lesson_plan_id}/export")
def export_lesson_plan(
    lesson_plan_id: uuid.UUID,
    format: Literal["pdf", "docx"] = "pdf",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    data, filename, media_type = export_service.export_lesson_plan(db, user, lesson_plan_id, format)
    return Response(content=data, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
