import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.ai.provider import AIProvider, get_ai_provider
from app.api.deps import get_current_user
from app.db.session import get_db
from app.export.docx import render_lesson_plan_docx
from app.export.pdf import render_lesson_plan_pdf
from app.models.class_ import Class
from app.models.curriculum import Subject, YearGroup
from app.models.lesson_plan import LessonPlan, LessonPlanVersion
from app.models.user import User
from app.schemas.lesson_plan import (
    AssignClassRequest,
    GenerateLessonPlanRequest,
    LessonPlanResponse,
    LessonPlanSummaryResponse,
    LessonPlanVersionResponse,
    RegenerateSectionRequest,
    SaveVersionRequest,
)
from app.schemas.lesson_plan_content import REGENERATABLE_SECTIONS, LessonPlanContent
from app.services import auth_service, lesson_plan_service

router = APIRouter(prefix="/lesson-plans", tags=["lesson-plans"])
school_lesson_plans_router = APIRouter(prefix="/schools", tags=["lesson-plans"])


def _safe_header_filename(name: str) -> str:
    return name.replace("\\", "").replace('"', "").replace("\r", "").replace("\n", "")


def _require_ai_provider(ai_provider: AIProvider | None = Depends(get_ai_provider)) -> AIProvider:
    if ai_provider is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI generation is not configured on this server.")
    return ai_provider


def _version_response(db: Session, version: LessonPlanVersion) -> LessonPlanVersionResponse:
    return LessonPlanVersionResponse(
        id=version.id,
        version_number=version.version_number,
        content=LessonPlanContent.model_validate(version.content),
        generation_kind=version.generation_kind,
        generation_notes=version.generation_notes,
        safeguarding_flagged=version.safeguarding_flagged,
        safeguarding_notes=version.safeguarding_notes,
        resource_ids=lesson_plan_service.resource_ids_for_version(db, version),
        created_at=version.created_at,
    )


def _plan_response(db: Session, plan: LessonPlan) -> LessonPlanResponse:
    subject = db.get(Subject, plan.subject_id)
    year_group = db.get(YearGroup, plan.year_group_id)
    class_ = db.get(Class, plan.class_id) if plan.class_id else None
    current = lesson_plan_service.get_current_version(db, plan)
    return LessonPlanResponse(
        id=plan.id,
        subject_id=plan.subject_id,
        subject_name=subject.name,
        year_group_id=plan.year_group_id,
        year_group_name=year_group.name,
        topic_title=plan.topic_title,
        duration_minutes=plan.duration_minutes,
        ability_level=plan.ability_level,
        class_id=plan.class_id,
        class_name=class_.name if class_ else None,
        created_at=plan.created_at,
        current_version=_version_response(db, current),
    )


def _summary_response(db: Session, plan: LessonPlan) -> LessonPlanSummaryResponse:
    subject = db.get(Subject, plan.subject_id)
    year_group = db.get(YearGroup, plan.year_group_id)
    class_ = db.get(Class, plan.class_id) if plan.class_id else None
    owner = db.get(User, plan.owner_user_id)
    current = lesson_plan_service.get_current_version(db, plan)
    return LessonPlanSummaryResponse(
        id=plan.id,
        subject_id=plan.subject_id,
        subject_name=subject.name,
        year_group_id=plan.year_group_id,
        year_group_name=year_group.name,
        topic_title=plan.topic_title,
        duration_minutes=plan.duration_minutes,
        ability_level=plan.ability_level,
        class_id=plan.class_id,
        class_name=class_.name if class_ else None,
        owner_display_name=auth_service.get_display_name(db, owner),
        current_version_number=current.version_number,
        updated_at=plan.updated_at,
    )


@router.post("/generate", response_model=LessonPlanResponse, status_code=status.HTTP_201_CREATED)
def generate(
    payload: GenerateLessonPlanRequest,
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(_require_ai_provider),
    user: User = Depends(get_current_user),
) -> LessonPlanResponse:
    plan = lesson_plan_service.generate_lesson_plan(db, ai_provider, user, payload)
    return _plan_response(db, plan)


@router.get("", response_model=list[LessonPlanSummaryResponse])
def list_plans(
    subject_id: uuid.UUID | None = None,
    year_group_id: uuid.UUID | None = None,
    topic: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    class_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[LessonPlanSummaryResponse]:
    plans = lesson_plan_service.list_plans(
        db, user, subject_id=subject_id, year_group_id=year_group_id, topic=topic, date_from=date_from, date_to=date_to, class_id=class_id
    )
    return [_summary_response(db, p) for p in plans]


@router.patch("/{plan_id}/assign", response_model=LessonPlanResponse)
def assign_class(
    plan_id: uuid.UUID, payload: AssignClassRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> LessonPlanResponse:
    plan = lesson_plan_service.get_owned_plan(db, user, plan_id)
    plan = lesson_plan_service.assign_class(db, user, plan, payload.class_id)
    return _plan_response(db, plan)


@router.get("/{plan_id}", response_model=LessonPlanResponse)
def get_plan(plan_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> LessonPlanResponse:
    plan = lesson_plan_service.get_owned_plan(db, user, plan_id)
    return _plan_response(db, plan)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(plan_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    plan = lesson_plan_service.get_owned_plan(db, user, plan_id)
    lesson_plan_service.delete_plan(db, user, plan)


@router.post("/{plan_id}/duplicate", response_model=LessonPlanResponse, status_code=status.HTTP_201_CREATED)
def duplicate_plan(plan_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> LessonPlanResponse:
    plan = lesson_plan_service.get_owned_plan(db, user, plan_id)
    new_plan = lesson_plan_service.duplicate_plan(db, user, plan)
    return _plan_response(db, new_plan)


@router.get("/{plan_id}/versions", response_model=list[LessonPlanVersionResponse])
def list_versions(plan_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[LessonPlanVersionResponse]:
    plan = lesson_plan_service.get_owned_plan(db, user, plan_id)
    return [_version_response(db, v) for v in lesson_plan_service.list_versions(db, plan)]


@router.post("/{plan_id}/versions", response_model=LessonPlanVersionResponse, status_code=status.HTTP_201_CREATED)
def save_as_new_version(
    plan_id: uuid.UUID, payload: SaveVersionRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> LessonPlanVersionResponse:
    plan = lesson_plan_service.get_owned_plan(db, user, plan_id)
    version = lesson_plan_service.save_as_new_version(db, user, plan, payload.content)
    return _version_response(db, version)


@router.patch("/{plan_id}/versions/{version_id}", response_model=LessonPlanVersionResponse)
def save_edit(
    plan_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: SaveVersionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LessonPlanVersionResponse:
    plan = lesson_plan_service.get_owned_plan(db, user, plan_id)
    version = lesson_plan_service.save_edit(db, user, plan, version_id, payload.content)
    return _version_response(db, version)


@router.post("/{plan_id}/versions/{version_id}/restore", response_model=LessonPlanVersionResponse, status_code=status.HTTP_201_CREATED)
def restore_version(
    plan_id: uuid.UUID, version_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> LessonPlanVersionResponse:
    plan = lesson_plan_service.get_owned_plan(db, user, plan_id)
    version = lesson_plan_service.restore_version(db, user, plan, version_id)
    return _version_response(db, version)


@router.post("/{plan_id}/sections/{section_name}/regenerate", response_model=LessonPlanVersionResponse, status_code=status.HTTP_201_CREATED)
def regenerate_section(
    plan_id: uuid.UUID,
    section_name: str,
    payload: RegenerateSectionRequest,
    db: Session = Depends(get_db),
    ai_provider: AIProvider | None = Depends(get_ai_provider),
    user: User = Depends(get_current_user),
) -> LessonPlanVersionResponse:
    if section_name not in REGENERATABLE_SECTIONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{section_name}' is not a regeneratable section.")
    if ai_provider is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI generation is not configured on this server.")

    plan = lesson_plan_service.get_owned_plan(db, user, plan_id)
    version = lesson_plan_service.regenerate_section(db, ai_provider, user, plan, section_name, payload.instructions)
    return _version_response(db, version)


@router.get("/{plan_id}/versions/{version_id}/export.pdf")
def export_pdf(plan_id: uuid.UUID, version_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    plan = lesson_plan_service.get_owned_plan(db, user, plan_id)
    version = lesson_plan_service.get_version(db, plan, version_id)
    subject = db.get(Subject, plan.subject_id)
    year_group = db.get(YearGroup, plan.year_group_id)
    content = LessonPlanContent.model_validate(version.content)
    pdf_bytes = render_lesson_plan_pdf(content, subject.name, year_group.name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_safe_header_filename(content.title)}.pdf"'},
    )


@router.get("/{plan_id}/versions/{version_id}/export.docx")
def export_docx(plan_id: uuid.UUID, version_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    plan = lesson_plan_service.get_owned_plan(db, user, plan_id)
    version = lesson_plan_service.get_version(db, plan, version_id)
    subject = db.get(Subject, plan.subject_id)
    year_group = db.get(YearGroup, plan.year_group_id)
    content = LessonPlanContent.model_validate(version.content)
    docx_bytes = render_lesson_plan_docx(content, subject.name, year_group.name)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{_safe_header_filename(content.title)}.docx"'},
    )


@school_lesson_plans_router.get("/{school_id}/lesson-plans", response_model=list[LessonPlanSummaryResponse])
def list_school_lesson_plans(
    school_id: uuid.UUID,
    subject_id: uuid.UUID | None = None,
    year_group_id: uuid.UUID | None = None,
    topic: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    class_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[LessonPlanSummaryResponse]:
    """Read-only: a school admin browsing lesson plans created by teachers
    in their own school. Never reaches across school boundaries -- see
    lesson_plan_service.list_school_plans's assert_school_member call.
    """
    plans = lesson_plan_service.list_school_plans(
        db, user, school_id, subject_id=subject_id, year_group_id=year_group_id, topic=topic, date_from=date_from, date_to=date_to, class_id=class_id
    )
    return [_summary_response(db, p) for p in plans]


@school_lesson_plans_router.get("/{school_id}/lesson-plans/{plan_id}", response_model=LessonPlanResponse)
def get_school_lesson_plan(
    school_id: uuid.UUID, plan_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> LessonPlanResponse:
    plan = lesson_plan_service.get_school_plan(db, user, school_id, plan_id)
    return _plan_response(db, plan)
