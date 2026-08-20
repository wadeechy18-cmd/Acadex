import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.question import Difficulty, QuestionType


class QuestionOptionSafe(BaseModel):
    """Options as shown to a student before answering — never reveals which one
    is correct.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    order_index: int


class QuestionOptionCreate(BaseModel):
    text: str = Field(min_length=1)
    is_correct: bool = False
    order_index: int = 0


class QuestionSafe(BaseModel):
    """A question as presented for practice — no answer key included."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID
    exam_board_id: uuid.UUID | None
    chapter_id: uuid.UUID | None
    topic_id: uuid.UUID | None
    question_type: QuestionType
    difficulty: Difficulty
    marks: int
    prompt: str
    options: list[QuestionOptionSafe] = []


class QuestionCreate(BaseModel):
    subject_id: uuid.UUID
    exam_board_id: uuid.UUID | None = None
    chapter_id: uuid.UUID | None = None
    topic_id: uuid.UUID | None = None
    question_type: QuestionType
    difficulty: Difficulty = Difficulty.MEDIUM
    marks: int = Field(default=1, ge=1)
    prompt: str = Field(min_length=1)
    correct_answer: str | None = None
    explanation: str | None = None
    is_published: bool = False
    options: list[QuestionOptionCreate] = []


class AnswerCheckRequest(BaseModel):
    answer: str


class AnswerCheckResult(BaseModel):
    is_correct: bool | None
    correct_answer: str | None
    explanation: str | None
