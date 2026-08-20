import uuid
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class QuestionType(str, PyEnum):
    MCQ = "mcq"
    SHORT_ANSWER = "short_answer"
    NUMERICAL = "numerical"
    TRUE_FALSE = "true_false"
    STRUCTURED = "structured"


class Difficulty(str, PyEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class TopicTag(UUIDPKMixin, TimestampMixin, Base):
    """Free-form subtopic tags (e.g. 'Quadratic formula', 'Completing the square')
    independent of the primary Chapter/Topic FK, so a question can be tagged with
    multiple fine-grained subtopics for targeted practice.
    """

    __tablename__ = "topic_tags"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)


question_topic_tags = Table(
    "question_topic_tags",
    Base.metadata,
    Column("question_id", UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True),
    Column("topic_tag_id", UUID(as_uuid=True), ForeignKey("topic_tags.id", ondelete="CASCADE"), primary_key=True),
)


class Question(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "questions"

    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exam_board_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exam_boards.id", ondelete="SET NULL")
    )
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="SET NULL")
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), index=True
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType, name="question_type"), nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty, name="question_difficulty"), nullable=False)
    marks: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str | None] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    options: Mapped[list["QuestionOption"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", order_by="QuestionOption.order_index"
    )
    topic_tags: Mapped[list["TopicTag"]] = relationship(secondary=question_topic_tags)


class QuestionOption(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "question_options"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    question: Mapped["Question"] = relationship(back_populates="options")
