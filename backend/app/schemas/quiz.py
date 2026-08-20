import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.question import QuestionSafe


class QuizResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    topic_id: uuid.UUID | None
    chapter_id: uuid.UUID | None
    title: str
    has_timer: bool
    time_limit_seconds: int | None
    is_published: bool


class QuizCreate(BaseModel):
    topic_id: uuid.UUID | None = None
    chapter_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    has_timer: bool = False
    time_limit_seconds: int | None = Field(default=None, ge=1)
    question_ids: list[uuid.UUID] = Field(default_factory=list)


class QuizDetail(QuizResponse):
    questions: list[QuestionSafe]


class QuizAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    started_at: datetime | None
    submitted_at: datetime | None
    score: float | None
    percentage: float | None


class AnswerSubmission(BaseModel):
    question_id: uuid.UUID
    answer: str


class QuizSubmission(BaseModel):
    answers: list[AnswerSubmission]


class QuizAnswerResult(BaseModel):
    question_id: uuid.UUID
    student_answer: str | None
    is_correct: bool | None
    correct_answer: str | None
    explanation: str | None


class QuizAttemptResult(QuizAttemptResponse):
    answers: list[QuizAnswerResult]
