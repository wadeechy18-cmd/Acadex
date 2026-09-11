import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.ai.provider import AIProvider, get_ai_provider
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.worksheet import Worksheet
from app.planning.worksheet_builder import build_answer_key, estimate_minutes, total_marks
from app.schemas.worksheet import (
    AnswerKey,
    PracticeSetContent,
    WorksheetAIGenerateRequest,
    WorksheetCreate,
    WorksheetResponse,
    WorksheetUpdate,
)
from app.services import export_service, practice_set_service

router = APIRouter(tags=["worksheets"])


def _to_response(worksheet: Worksheet) -> WorksheetResponse:
    content = PracticeSetContent.model_validate(worksheet.content)
    return WorksheetResponse(
        id=worksheet.id,
        lesson_plan_id=worksheet.lesson_plan_id,
        title=worksheet.title,
        content=content,
        total_marks=total_marks(content),
        estimated_minutes=estimate_minutes(content),
        created_at=worksheet.created_at,
        updated_at=worksheet.updated_at,
    )


@router.post(
    "/lesson-plans/{lesson_plan_id}/worksheets", response_model=WorksheetResponse, status_code=status.HTTP_201_CREATED
)
def create_worksheet(
    lesson_plan_id: uuid.UUID,
    payload: WorksheetCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorksheetResponse:
    worksheet = practice_set_service.create(
        db, user, Worksheet, lesson_plan_id, title=payload.title, content=payload.content
    )
    return _to_response(worksheet)


@router.get("/lesson-plans/{lesson_plan_id}/worksheets", response_model=list[WorksheetResponse])
def list_worksheets(
    lesson_plan_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[WorksheetResponse]:
    worksheets = practice_set_service.list_for_lesson_plan(db, user, Worksheet, lesson_plan_id)
    return [_to_response(w) for w in worksheets]


@router.get("/worksheets/{worksheet_id}", response_model=WorksheetResponse)
def get_worksheet(
    worksheet_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> WorksheetResponse:
    worksheet = practice_set_service.get_one(db, user, Worksheet, worksheet_id)
    return _to_response(worksheet)


@router.get("/worksheets/{worksheet_id}/answer-key", response_model=AnswerKey)
def get_worksheet_answer_key(
    worksheet_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> AnswerKey:
    worksheet = practice_set_service.get_one(db, user, Worksheet, worksheet_id)
    return build_answer_key(PracticeSetContent.model_validate(worksheet.content))


@router.patch("/worksheets/{worksheet_id}", response_model=WorksheetResponse)
def update_worksheet(
    worksheet_id: uuid.UUID,
    payload: WorksheetUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorksheetResponse:
    worksheet = practice_set_service.update(
        db, user, Worksheet, worksheet_id, updates=payload.model_dump(exclude_unset=True)
    )
    return _to_response(worksheet)


@router.delete("/worksheets/{worksheet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_worksheet(
    worksheet_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    practice_set_service.delete(db, user, Worksheet, worksheet_id)


@router.get("/worksheets/{worksheet_id}/export")
def export_worksheet(
    worksheet_id: uuid.UUID,
    format: Literal["pdf", "docx"] = "pdf",
    include_answers: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    data, filename, media_type = export_service.export_practice_set(db, user, Worksheet, worksheet_id, format, include_answers)
    return Response(content=data, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/lesson-plans/{lesson_plan_id}/worksheets/ai-generate", response_model=PracticeSetContent)
def ai_generate_worksheet(
    lesson_plan_id: uuid.UUID,
    payload: WorksheetAIGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    provider: AIProvider | None = Depends(get_ai_provider),
) -> PracticeSetContent:
    if provider is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI features are not configured for this deployment.")
    return practice_set_service.generate_content_with_ai(
        db,
        user,
        lesson_plan_id,
        kind="worksheet",
        instructions=payload.instructions,
        item_count=payload.item_count,
        resource_ids=payload.resource_ids,
        provider=provider,
    )
