import uuid
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
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
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True)
    year_group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("year_groups.id"), nullable=False, index=True)
    curriculum_topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("curriculum_topics.id"), nullable=True
    )
    topic_title: Mapped[str] = mapped_column(String(300), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    ability_level: Mapped[AbilityLevel] = mapped_column(Enum(AbilityLevel, name="ability_level"), nullable=False)


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
