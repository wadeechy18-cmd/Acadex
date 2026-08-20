import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional, require_teacher_or_admin
from app.db.session import get_db
from app.models.question import Difficulty, Question, QuestionOption, QuestionType
from app.models.user import User
from app.schemas.question import (
    AnswerCheckRequest,
    AnswerCheckResult,
    QuestionCreate,
    QuestionSafe,
)
from app.services.education_service import assert_can_manage_subject
from app.services.quiz_service import check_single_answer, resolve_correct_answer_display

router = APIRouter(tags=["practice"])


@router.get("/questions", response_model=list[QuestionSafe])
def list_questions(
    subject_id: uuid.UUID | None = None,
    chapter_id: uuid.UUID | None = None,
    topic_id: uuid.UUID | None = None,
    exam_board_id: uuid.UUID | None = None,
    difficulty: Difficulty | None = None,
    question_type: QuestionType | None = None,
    db: Session = Depends(get_db),
) -> list[Question]:
    query = db.query(Question).filter(Question.is_published.is_(True))
    if subject_id:
        query = query.filter(Question.subject_id == subject_id)
    if chapter_id:
        query = query.filter(Question.chapter_id == chapter_id)
    if topic_id:
        query = query.filter(Question.topic_id == topic_id)
    if exam_board_id:
        query = query.filter(Question.exam_board_id == exam_board_id)
    if difficulty:
        query = query.filter(Question.difficulty == difficulty)
    if question_type:
        query = query.filter(Question.question_type == question_type)
    return query.all()


@router.get("/questions/{question_id}", response_model=QuestionSafe)
def get_question(question_id: uuid.UUID, db: Session = Depends(get_db)) -> Question:
    question = db.query(Question).filter_by(id=question_id, is_published=True).first()
    if not question:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found.")
    return question


@router.post("/questions/{question_id}/check", response_model=AnswerCheckResult)
def check_answer(question_id: uuid.UUID, payload: AnswerCheckRequest, db: Session = Depends(get_db)) -> AnswerCheckResult:
    question = db.query(Question).filter_by(id=question_id, is_published=True).first()
    if not question:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found.")

    is_correct = check_single_answer(db, question, payload.answer)

    return AnswerCheckResult(
        is_correct=is_correct,
        correct_answer=resolve_correct_answer_display(db, question),
        explanation=question.explanation,
    )


@router.post("/questions", response_model=QuestionSafe, status_code=status.HTTP_201_CREATED)
def create_question(
    payload: QuestionCreate, db: Session = Depends(get_db), user: User = Depends(require_teacher_or_admin)
) -> Question:
    assert_can_manage_subject(db, user, payload.subject_id)

    data = payload.model_dump(exclude={"options"})
    question = Question(**data, created_by_id=user.id)
    db.add(question)
    db.flush()

    for option in payload.options:
        db.add(QuestionOption(question_id=question.id, **option.model_dump()))

    db.commit()
    db.refresh(question)
    return question
