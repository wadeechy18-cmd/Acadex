import uuid
from datetime import date
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class AbilityLevel(str, PyEnum):
    SUPPORT = "support"
    CORE = "core"
    GREATER_DEPTH = "greater_depth"
    MIXED = "mixed"


class GenerationKind(str, PyEnum):
    FULL_GENERATION = "full_generation"
    SECTION_REGENERATION = "section_regeneration"
    MANUAL_EDIT = "manual_edit"


class LessonPlan(UUIDPKMixin, TimestampMixin, Base):
    """The stable identity of a lesson plan -- its actual content always
    lives in the current (highest version_number) LessonPlanVersion, never
    here. See LessonPlanVersion's docstring for why.
    """

    __tablename__ = "lesson_plans"

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Stamped from the teacher's school membership at creation time (null if
    # they have none) so a school admin can later browse lesson plans
    # created within their own school -- see assert_school_member.
    school_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="SET NULL"), nullable=True, index=True
    )
    class_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("classes.id", ondelete="SET NULL"), nullable=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True)
    year_group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("year_groups.id"), nullable=False, index=True)
    curriculum_topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("curriculum_topics.id"), nullable=True
    )
    topic_title: Mapped[str] = mapped_column(String(300), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    ability_level: Mapped[AbilityLevel] = mapped_column(Enum(AbilityLevel, name="ability_level"), nullable=False)
    # Set when a teacher asks for a lesson "for tomorrow" / a named date via
    # the quick-generate flow (app/planning/date_resolution.py resolves the
    # phrase deterministically); null for plans built through the detailed
    # form, which never asks for a date.
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class LessonPlanVersion(UUIDPKMixin, TimestampMixin, Base):
    """Append-only: "current" is always the row with the highest
    version_number for a given lesson_plan_id, not a separate pointer
    column -- the same pattern used elsewhere in this codebase, so there's
    never a current-pointer and a max-version-row to keep in sync.
    """

    __tablename__ = "lesson_plan_versions"
    __table_args__ = (UniqueConstraint("lesson_plan_id", "version_number", name="uq_lesson_plan_version_number"),)

    lesson_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lesson_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Worksheet/homework are generated alongside the lesson and versioned
    # with it, but stored in their own columns (rather than folded into
    # `content`) since they're independently regeneratable and translatable.
    # Null only for versions created before this feature existed.
    worksheet_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    homework_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Cached Bangla translation of (content, worksheet_content,
    # homework_content) -- see app/planning/translation.py. Never generated
    # eagerly; populated on first request for this version, then reused.
    translation_bn: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    generation_kind: Mapped[GenerationKind] = mapped_column(Enum(GenerationKind, name="lesson_plan_generation_kind"), nullable=False)
    generation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    safeguarding_flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    safeguarding_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class LessonPlanVersionResource(UUIDPKMixin, TimestampMixin, Base):
    """Which resources were fed to the AI as context for a given version --
    tracked per-version (not per-plan) since a regeneration can use a
    different resource set than the version before it.
    """

    __tablename__ = "lesson_plan_version_resources"
    __table_args__ = (UniqueConstraint("lesson_plan_version_id", "resource_id", name="uq_version_resource"),)

    lesson_plan_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lesson_plan_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True
    )
