import uuid
from enum import Enum as PyEnum

from sqlalchemy import JSON, Boolean, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class VoteValue(int, PyEnum):
    UP = 1
    DOWN = -1


class VoteTargetType(str, PyEnum):
    COMMENT = "comment"


class ReportTargetType(str, PyEnum):
    COMMENT = "comment"
    QUESTION_THREAD = "question_thread"


class ReportStatus(str, PyEnum):
    PENDING = "pending"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class QuestionThreadStatus(str, PyEnum):
    OPEN = "open"
    ANSWERED = "answered"
    CLOSED = "closed"


class Discussion(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "discussions"

    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    comments: Mapped[list["Comment"]] = relationship(back_populates="discussion", cascade="all, delete-orphan")


class Comment(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "comments"

    discussion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discussions.id", ondelete="CASCADE"), index=True
    )
    question_thread_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("question_threads.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comments.id", ondelete="CASCADE")
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_verified_teacher_answer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    discussion: Mapped["Discussion | None"] = relationship(back_populates="comments")
    replies: Mapped[list["Comment"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan", single_parent=True
    )
    parent: Mapped["Comment | None"] = relationship(remote_side="Comment.id", back_populates="replies")


class QuestionThread(UUIDPKMixin, TimestampMixin, Base):
    """The 'Ask a Question' feature: a student uploads a photo of a question,
    optionally with a description, tagged to a subject/topic. AI analysis of the
    image is a future addition — the `QuestionImage.ai_analysis` column exists now
    so that feature is additive, not a schema change.
    """

    __tablename__ = "question_threads"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL")
    )
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[QuestionThreadStatus] = mapped_column(
        Enum(QuestionThreadStatus, name="question_thread_status"),
        default=QuestionThreadStatus.OPEN,
        nullable=False,
    )

    images: Mapped[list["QuestionImage"]] = relationship(back_populates="thread", cascade="all, delete-orphan")


class QuestionImage(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "question_images"

    question_thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("question_threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    ai_analysis: Mapped[dict | None] = mapped_column(JSON)

    thread: Mapped["QuestionThread"] = relationship(back_populates="images")


class Vote(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("user_id", "target_type", "target_id", name="uq_vote_user_target"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_type: Mapped[VoteTargetType] = mapped_column(Enum(VoteTargetType, name="vote_target_type"), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)


class Report(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "reports"

    reported_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    target_type: Mapped[ReportTargetType] = mapped_column(
        Enum(ReportTargetType, name="report_target_type"), nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status"), default=ReportStatus.PENDING, nullable=False
    )
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
