import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_student, require_teacher_or_admin
from app.db.session import get_db
from app.models.question import Question
from app.models.quiz import Quiz, QuizAnswer, QuizAttempt, QuizQuestion
from app.models.user import User
from app.schemas.question import QuestionSafe
from app.schemas.quiz import (
    QuizAnswerResult,
    QuizAttemptResponse,
    QuizAttemptResult,
    QuizCreate,
    QuizDetail,
    QuizResponse,
    QuizSubmission,
)
from app.services.education_service import assert_can_manage_chapter, assert_can_manage_topic
from app.services.quiz_service import grade_quiz_answers, resolve_correct_answer_display, start_attempt, submit_attempt

router = APIRouter(tags=["quiz"])


@router.get("/quizzes", response_model=list[QuizResponse])
def list_quizzes(
    topic_id: uuid.UUID | None = None, chapter_id: uuid.UUID | None = None, db: Session = Depends(get_db)
) -> list[Quiz]:
    query = db.query(Quiz).filter(Quiz.is_published.is_(True))
    if topic_id:
        query = query.filter(Quiz.topic_id == topic_id)
    if chapter_id:
        query = query.filter(Quiz.chapter_id == chapter_id)
    return query.all()


@router.get("/quizzes/{quiz_id}", response_model=QuizDetail)
def get_quiz(quiz_id: uuid.UUID, db: Session = Depends(get_db)) -> QuizDetail:
    quiz = db.query(Quiz).filter_by(id=quiz_id, is_published=True).first()
    if not quiz:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz not found.")

    quiz_questions = (
        db.query(QuizQuestion).filter_by(quiz_id=quiz.id).order_by(QuizQuestion.order_index).all()
    )
    questions = [db.get(Question, qq.question_id) for qq in quiz_questions]

    return QuizDetail(
        id=quiz.id,
        topic_id=quiz.topic_id,
        chapter_id=quiz.chapter_id,
        title=quiz.title,
        has_timer=quiz.has_timer,
        time_limit_seconds=quiz.time_limit_seconds,
        is_published=quiz.is_published,
        questions=[QuestionSafe.model_validate(q) for q in questions if q],
    )


@router.post("/quizzes/{quiz_id}/check", response_model=QuizAttemptResult)
def check_quiz(quiz_id: uuid.UUID, payload: QuizSubmission, db: Session = Depends(get_db)) -> QuizAttemptResult:
    """Grades a quiz instantly with no login and nothing persisted — lets
    anyone take a quiz and see their score without an account.
    """
    quiz = db.query(Quiz).filter_by(id=quiz_id, is_published=True).first()
    if not quiz:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz not found.")

    graded, marks_earned, total_marks_available = grade_quiz_answers(
        db, quiz_id, [(a.question_id, a.answer) for a in payload.answers]
    )

    results = []
    for question_id, student_answer, is_correct in graded:
        question = db.get(Question, question_id)
        results.append(
            QuizAnswerResult(
                question_id=question_id,
                student_answer=student_answer,
                is_correct=is_correct,
                correct_answer=resolve_correct_answer_display(db, question) if question else None,
                explanation=question.explanation if question else None,
            )
        )

    now = datetime.now(timezone.utc)
    return QuizAttemptResult(
        id=uuid.uuid4(),
        quiz_id=quiz_id,
        started_at=now,
        submitted_at=now,
        score=marks_earned,
        percentage=round((marks_earned / total_marks_available) * 100, 1) if total_marks_available else 0.0,
        answers=results,
    )


@router.post("/quizzes", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
def create_quiz(payload: QuizCreate, db: Session = Depends(get_db), user: User = Depends(require_teacher_or_admin)) -> Quiz:
    if not payload.topic_id and not payload.chapter_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "A quiz must belong to a topic or a chapter.")
    if payload.topic_id:
        assert_can_manage_topic(db, user, payload.topic_id)
    if payload.chapter_id:
        assert_can_manage_chapter(db, user, payload.chapter_id)

    quiz = Quiz(
        topic_id=payload.topic_id,
        chapter_id=payload.chapter_id,
        title=payload.title,
        has_timer=payload.has_timer,
        time_limit_seconds=payload.time_limit_seconds,
    )
    db.add(quiz)
    db.flush()

    for i, question_id in enumerate(payload.question_ids):
        db.add(QuizQuestion(quiz_id=quiz.id, question_id=question_id, order_index=i))

    db.commit()
    db.refresh(quiz)
    return quiz


@router.post("/quizzes/{quiz_id}/attempts", response_model=QuizAttemptResponse, status_code=status.HTTP_201_CREATED)
def create_attempt(quiz_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_student)) -> QuizAttempt:
    return start_attempt(db, user.id, quiz_id)


@router.post("/quiz-attempts/{attempt_id}/submit", response_model=QuizAttemptResult)
def submit_quiz_attempt(
    attempt_id: uuid.UUID,
    payload: QuizSubmission,
    db: Session = Depends(get_db),
    user: User = Depends(require_student),
) -> QuizAttemptResult:
    attempt = submit_attempt(db, user.id, attempt_id, [(a.question_id, a.answer) for a in payload.answers])

    answer_rows = db.query(QuizAnswer).filter_by(attempt_id=attempt.id).all()
    results = []
    for row in answer_rows:
        question = db.get(Question, row.question_id)
        results.append(
            QuizAnswerResult(
                question_id=row.question_id,
                student_answer=row.student_answer,
                is_correct=row.is_correct,
                correct_answer=resolve_correct_answer_display(db, question) if question else None,
                explanation=question.explanation if question else None,
            )
        )

    return QuizAttemptResult(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at,
        score=attempt.score,
        percentage=attempt.percentage,
        answers=results,
    )


@router.get("/quiz-attempts/me", response_model=list[QuizAttemptResponse])
def list_my_attempts(
    quiz_id: uuid.UUID | None = None, db: Session = Depends(get_db), user: User = Depends(require_student)
) -> list[QuizAttempt]:
    query = db.query(QuizAttempt).filter(QuizAttempt.student_id == user.id)
    if quiz_id:
        query = query.filter(QuizAttempt.quiz_id == quiz_id)
    return query.order_by(QuizAttempt.created_at.desc()).all()
