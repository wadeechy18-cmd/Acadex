import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.provider import AIProvider, get_ai_provider
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.worksheet import Homework
from app.planning.worksheet_builder import build_answer_key, estimate_minutes, total_marks
from app.schemas.homework import (
    HomeworkAIGenerateRequest,
    HomeworkCreate,
    HomeworkResponse,
    HomeworkUpdate,
)
from app.schemas.worksheet import AnswerKey, PracticeSetContent
from app.services import practice_set_service

router = APIRouter(tags=["homework"])


def _to_response(homework: Homework) -> HomeworkResponse:
    content = PracticeSetContent.model_validate(homework.content)
    return HomeworkResponse(
        id=homework.id,
        lesson_plan_id=homework.lesson_plan_id,
        title=homework.title,
        content=content,
        total_marks=total_marks(content),
        estimated_minutes=estimate_minutes(content),
        due_date=homework.due_date,
        created_at=homework.created_at,
        updated_at=homework.updated_at,
    )


@router.post(
    "/lesson-plans/{lesson_plan_id}/homework", response_model=HomeworkResponse, status_code=status.HTTP_201_CREATED
)
def create_homework(
    lesson_plan_id: uuid.UUID,
    payload: HomeworkCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HomeworkResponse:
    homework = practice_set_service.create(
        db,
        user,
        Homework,
        lesson_plan_id,
        title=payload.title,
        content=payload.content,
        extra_fields={"due_date": payload.due_date},
    )
    return _to_response(homework)


@router.get("/lesson-plans/{lesson_plan_id}/homework", response_model=list[HomeworkResponse])
def list_homework(
    lesson_plan_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[HomeworkResponse]:
    homework_items = practice_set_service.list_for_lesson_plan(db, user, Homework, lesson_plan_id)
    return [_to_response(h) for h in homework_items]


@router.get("/homework/{homework_id}", response_model=HomeworkResponse)
def get_homework(
    homework_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> HomeworkResponse:
    homework = practice_set_service.get_one(db, user, Homework, homework_id)
    return _to_response(homework)


@router.get("/homework/{homework_id}/answer-key", response_model=AnswerKey)
def get_homework_answer_key(
    homework_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> AnswerKey:
    homework = practice_set_service.get_one(db, user, Homework, homework_id)
    return build_answer_key(PracticeSetContent.model_validate(homework.content))


@router.patch("/homework/{homework_id}", response_model=HomeworkResponse)
def update_homework(
    homework_id: uuid.UUID,
    payload: HomeworkUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HomeworkResponse:
    homework = practice_set_service.update(
        db, user, Homework, homework_id, updates=payload.model_dump(exclude_unset=True)
    )
    return _to_response(homework)


@router.delete("/homework/{homework_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_homework(
    homework_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    practice_set_service.delete(db, user, Homework, homework_id)


@router.post("/lesson-plans/{lesson_plan_id}/homework/ai-generate", response_model=PracticeSetContent)
def ai_generate_homework(
    lesson_plan_id: uuid.UUID,
    payload: HomeworkAIGenerateRequest,
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
        kind="homework",
        instructions=payload.instructions,
        item_count=payload.item_count,
        resource_ids=payload.resource_ids,
        provider=provider,
    )
