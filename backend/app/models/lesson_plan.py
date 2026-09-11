import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class LessonPlanStatus(str, PyEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class LessonPlanTemplateType(str, PyEnum):
    STANDARD = "standard"
    PRACTICAL = "practical"
    REVISION = "revision"
    EXAM_PREP = "exam_prep"
    NEW_TOPIC = "new_topic"
    RETRIEVAL = "retrieval"
    ASSESSMENT = "assessment"
    REVIEW = "review"
    DOUBLE = "double"
    SHORT = "short"


class LessonPlan(UUIDPKMixin, TimestampMixin, Base):
    """A teacher's day-to-day teaching document -- unrelated to the existing
    `Lesson` model (published, student-facing video+notes content). Content
    itself lives in LessonPlanVersion, never here, so every save is a new
    immutable version rather than an overwrite.
    """

    __tablename__ = "lesson_plans"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    teacher_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    topic: Mapped[str] = mapped_column(String(250), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    template_type: Mapped[LessonPlanTemplateType] = mapped_column(
        Enum(LessonPlanTemplateType, name="lesson_plan_template_type"),
        default=LessonPlanTemplateType.STANDARD,
        nullable=False,
    )
    status: Mapped[LessonPlanStatus] = mapped_column(
        Enum(LessonPlanStatus, name="lesson_plan_status"), default=LessonPlanStatus.DRAFT, nullable=False
    )


class LessonPlanVersion(UUIDPKMixin, Base):
    """Immutable snapshot of a lesson plan's structured content. "Current"
    version is simply the row with the highest version_number for a given
    lesson_plan_id -- no current_version_id pointer on LessonPlan, which
    would need a circular FK and a second place that could drift out of
    sync with the actual latest row.
    """

    __tablename__ = "lesson_plan_versions"
    __table_args__ = (UniqueConstraint("lesson_plan_id", "version_number", name="uq_lesson_plan_version_number"),)

    lesson_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lesson_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
