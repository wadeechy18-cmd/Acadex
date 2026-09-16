import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.ai.provider import AIProvider, get_ai_provider
from app.api.deps import get_current_user
from app.db.session import get_db
from app.export.docx import render_homework_docx, render_lesson_plan_docx, render_worksheet_docx
from app.export.pdf import render_homework_pdf, render_lesson_plan_pdf, render_worksheet_pdf
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
from app.schemas.lesson_plan_content import REGENERATABLE_SECTIONS, HomeworkContent, LessonPlanContent, TranslatedContent, WorksheetContent
from app.schemas.quick_lesson import QuickGenerateRequest, TopicProgressEntry
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
        worksheet=WorksheetContent.model_validate(version.worksheet_content) if version.worksheet_content else None,
        homework_task=HomeworkContent.model_validate(version.homework_content) if version.homework_content else None,
        translation_bn=TranslatedContent.model_validate(version.translation_bn) if version.translation_bn else None,
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
        scheduled_date=plan.scheduled_date,
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
        scheduled_date=plan.scheduled_date,
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


@router.post("/quick-generate", response_model=LessonPlanResponse, status_code=status.HTTP_201_CREATED)
def quick_generate(
    payload: QuickGenerateRequest,
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(_require_ai_provider),
    user: User = Depends(get_current_user),
) -> LessonPlanResponse:
    """The "what do you want to teach?" entry point -- one sentence in, a
    complete lesson (plus worksheet and homework, drawn from the teacher's
    own resource library) out. See lesson_plan_service.quick_generate_from_text.
    """
    plan = lesson_plan_service.quick_generate_from_text(db, ai_provider, user, payload.text)
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


@router.get("/topic-suggestions", response_model=list[TopicProgressEntry])
def topic_suggestions(
    subject_id: uuid.UUID, year_group_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[TopicProgressEntry]:
    """Feeds the optional topic picker: every topic in curriculum sequence
    for this subject/year group, each flagged with whether this teacher
    has already covered it and which one Acadex would pick automatically
    (new-vs-existing-teacher progression -- see lesson_plan_service).
    """
    return [TopicProgressEntry(**entry) for entry in lesson_plan_service.list_topic_progress(db, user, subject_id, year_group_id)]


@router.get("/library", response_model=list[LessonPlanSummaryResponse])
def list_library_plans(
    subject_id: uuid.UUID | None = None,
    year_group_id: uuid.UUID | None = None,
    topic: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[LessonPlanSummaryResponse]:
    """Pre-authored EYFS/KS1 lesson plans every teacher can browse -- see
    scripts/seed_lesson_plan_library.py. Never editable in place; a teacher
    copies one into their own plans via the duplicate endpoint below.
    """
    plans = lesson_plan_service.list_library_plans(db, subject_id=subject_id, year_group_id=year_group_id, topic=topic, limit=limit)
    return [_summary_response(db, p) for p in plans]


@router.get("/library/{plan_id}", response_model=LessonPlanResponse)
def get_library_plan(plan_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> LessonPlanResponse:
    plan = lesson_plan_service.get_library_plan(db, plan_id)
    return _plan_response(db, plan)


@router.post("/library/{plan_id}/duplicate", response_model=LessonPlanResponse, status_code=status.HTTP_201_CREATED)
def duplicate_library_plan(plan_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> LessonPlanResponse:
    new_plan = lesson_plan_service.duplicate_library_plan(db, user, plan_id)
    return _plan_response(db, new_plan)


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
    version = lesson_plan_service.save_as_new_version(db, user, plan, payload.content, payload.worksheet, payload.homework_task)
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
    version = lesson_plan_service.save_edit(db, user, plan, version_id, payload.content, payload.worksheet, payload.homework_task)
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


@router.post("/{plan_id}/worksheet/regenerate", response_model=LessonPlanVersionResponse, status_code=status.HTTP_201_CREATED)
def regenerate_worksheet(
    plan_id: uuid.UUID,
    payload: RegenerateSectionRequest,
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(_require_ai_provider),
    user: User = Depends(get_current_user),
) -> LessonPlanVersionResponse:
    plan = lesson_plan_service.get_owned_plan(db, user, plan_id)
    version = lesson_plan_service.regenerate_worksheet(db, ai_provider, user, plan, payload.instructions)
    return _version_response(db, version)


@router.post("/{plan_id}/homework/regenerate", response_model=LessonPlanVersionResponse, status_code=status.HTTP_201_CREATED)
def regenerate_homework(
    plan_id: uuid.UUID,
    payload: RegenerateSectionRequest,
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(_require_ai_provider),
    user: User = Depends(get_current_user),
) -> LessonPlanVersionResponse:
    plan = lesson_plan_service.get_owned_plan(db, user, plan_id)
    version = lesson_plan_service.regenerate_homework(db, ai_provider, user, plan, payload.instructions)
    return _version_response(db, version)


@router.post("/{plan_id}/versions/{version_id}/translate", response_model=LessonPlanVersionResponse)
def translate_version(
    plan_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(_require_ai_provider),
    user: User = Depends(get_current_user),
) -> LessonPlanVersionResponse:
    """Cached (see lesson_plan_service.translate_version) -- calling this
    again for a version that already has a translation just returns it.
    """
    plan = lesson_plan_service.get_owned_plan(db, user, plan_id)
    version = lesson_plan_service.translate_version(db, ai_provider, user, plan, version_id)
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


def _get_worksheet_or_404(version: LessonPlanVersion) -> WorksheetContent:
    if not version.worksheet_content:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This version has no worksheet.")
    return WorksheetContent.model_validate(version.worksheet_content)


def _get_homework_or_404(version: LessonPlanVersion) -> HomeworkContent:
    if not version.homework_content:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This version has no homework.")
    return HomeworkContent.model_validate(version.homework_content)


@router.get("/{plan_id}/versions/{version_id}/worksheet/export.pdf")
def export_worksheet_pdf(
    plan_id: uuid.UUID, version_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    plan = lesson_plan_service.get_owned_plan(db, user, plan_id)
    version = lesson_plan_service.get_version(db, plan, version_id)
    worksheet = _get_worksheet_or_404(version)
    subject = db.get(Subject, plan.subject_id)
    year_group = db.get(YearGroup, plan.year_group_id)
    pdf_bytes = render_worksheet_pdf(worksheet, subject.name, year_group.name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_safe_header_filename(worksheet.title)}.pdf"'},
    )


@router.get("/{plan_id}/versions/{version_id}/worksheet/export.docx")
def export_worksheet_docx(
    plan_id: uuid.UUID, version_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    plan = lesson_plan_service.get_owned_plan(db, user, plan_id)
    version = lesson_plan_service.get_version(db, plan, version_id)
    worksheet = _get_worksheet_or_404(version)
    subject = db.get(Subject, plan.subject_id)
    year_group = db.get(YearGroup, plan.year_group_id)
    docx_bytes = render_worksheet_docx(worksheet, subject.name, year_group.name)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{_safe_header_filename(worksheet.title)}.docx"'},
    )


@router.get("/{plan_id}/versions/{version_id}/homework/export.pdf")
def export_homework_pdf(
    plan_id: uuid.UUID, version_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    plan = lesson_plan_service.get_owned_plan(db, user, plan_id)
    version = lesson_plan_service.get_version(db, plan, version_id)
    homework_task = _get_homework_or_404(version)
    subject = db.get(Subject, plan.subject_id)
    year_group = db.get(YearGroup, plan.year_group_id)
    pdf_bytes = render_homework_pdf(homework_task, subject.name, year_group.name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_safe_header_filename(homework_task.title)}.pdf"'},
    )


@router.get("/{plan_id}/versions/{version_id}/homework/export.docx")
def export_homework_docx(
    plan_id: uuid.UUID, version_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    plan = lesson_plan_service.get_owned_plan(db, user, plan_id)
    version = lesson_plan_service.get_version(db, plan, version_id)
    homework_task = _get_homework_or_404(version)
    subject = db.get(Subject, plan.subject_id)
    year_group = db.get(YearGroup, plan.year_group_id)
    docx_bytes = render_homework_docx(homework_task, subject.name, year_group.name)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{_safe_header_filename(homework_task.title)}.docx"'},
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
