import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.question import Question, QuestionOption, QuestionType
from app.models.quiz import Quiz, QuizAnswer, QuizAttempt, QuizQuestion


def mark_answer(db: Session, question: Question, student_answer: str) -> bool | None:
    """Returns True/False for auto-markable question types, or None when the
    question requires human/teacher review (short answer, structured).
    """
    if question.question_type in (QuestionType.MCQ, QuestionType.TRUE_FALSE):
        correct_option = db.query(QuestionOption).filter_by(question_id=question.id, is_correct=True).first()
        return bool(correct_option) and str(correct_option.id) == student_answer.strip()

    if question.question_type == QuestionType.NUMERICAL:
        if question.correct_answer is None:
            return None
        try:
            return abs(float(student_answer) - float(question.correct_answer)) < 1e-6
        except ValueError:
            return student_answer.strip() == question.correct_answer.strip()

    return None


def check_single_answer(db: Session, question: Question, answer: str) -> bool | None:
    return mark_answer(db, question, answer)


def resolve_correct_answer_display(db: Session, question: Question) -> str | None:
    if question.question_type in (QuestionType.MCQ, QuestionType.TRUE_FALSE):
        correct_option = db.query(QuestionOption).filter_by(question_id=question.id, is_correct=True).first()
        return correct_option.text if correct_option else None
    return question.correct_answer


def grade_quiz_answers(
    db: Session, quiz_id: uuid.UUID, answers: list[tuple[uuid.UUID, str]]
) -> tuple[list[tuple[uuid.UUID, str, bool | None]], float, int]:
    """Marks a set of submitted answers against a quiz's questions without
    writing anything to the database. Returns (graded answers, marks earned,
    total marks available) so callers can either persist the result (a
    logged-in student's attempt) or just hand it back (anonymous practice).
    """
    quiz_question_rows = db.query(QuizQuestion).filter_by(quiz_id=quiz_id).all()
    marks_by_question = {qq.question_id: (qq.marks_override or None) for qq in quiz_question_rows}
    valid_question_ids = set(marks_by_question.keys())

    graded: list[tuple[uuid.UUID, str, bool | None]] = []
    total_marks_available = 0
    marks_earned = 0.0
    answered_ids: set[uuid.UUID] = set()

    for question_id, student_answer in answers:
        if question_id not in valid_question_ids:
            continue
        question = db.get(Question, question_id)
        if not question:
            continue

        answered_ids.add(question_id)
        is_correct = mark_answer(db, question, student_answer)
        graded.append((question_id, student_answer, is_correct))

        question_marks = marks_by_question[question_id] or question.marks
        total_marks_available += question_marks
        if is_correct:
            marks_earned += question_marks

    # Count marks for any questions in the quiz left unanswered.
    for question_id in valid_question_ids - answered_ids:
        question = db.get(Question, question_id)
        if question:
            total_marks_available += marks_by_question[question_id] or question.marks

    return graded, marks_earned, total_marks_available


def start_attempt(db: Session, student_id: uuid.UUID, quiz_id: uuid.UUID) -> QuizAttempt:
    quiz = db.get(Quiz, quiz_id)
    if not quiz or not quiz.is_published:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz not found.")

    attempt = QuizAttempt(quiz_id=quiz_id, student_id=student_id, started_at=datetime.now(timezone.utc))
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def submit_attempt(
    db: Session, student_id: uuid.UUID, attempt_id: uuid.UUID, answers: list[tuple[uuid.UUID, str]]
) -> QuizAttempt:
    attempt = db.query(QuizAttempt).filter_by(id=attempt_id, student_id=student_id).first()
    if not attempt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz attempt not found.")
    if attempt.submitted_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt has already been submitted.")

    graded, marks_earned, total_marks_available = grade_quiz_answers(db, attempt.quiz_id, answers)
    for question_id, student_answer, is_correct in graded:
        db.add(
            QuizAnswer(
                attempt_id=attempt.id,
                question_id=question_id,
                student_answer=student_answer,
                is_correct=is_correct,
            )
        )

    attempt.submitted_at = datetime.now(timezone.utc)
    attempt.score = marks_earned
    attempt.percentage = round((marks_earned / total_marks_available) * 100, 1) if total_marks_available else 0.0

    db.commit()
    db.refresh(attempt)
    return attempt
