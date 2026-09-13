import uuid
from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class SubstitutionPlanStatus(str, PyEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class AssignmentStatus(str, PyEnum):
    ASSIGNED = "assigned"
    UNFILLED = "unfilled"


class SubstitutionPlan(UUIDPKMixin, TimestampMixin, Base):
    """One plan per TeacherAbsence -- generating again replaces the
    previous plan and its assignments entirely (see
    app/services/substitution_service.py:generate_plan) rather than
    accumulating history, since a plan only matters until it's approved
    or rejected.
    """

    __tablename__ = "substitution_plans"
    __table_args__ = (UniqueConstraint("teacher_absence_id", name="uq_substitution_plan_absence"),)

    teacher_absence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teacher_absences.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[SubstitutionPlanStatus] = mapped_column(
        Enum(SubstitutionPlanStatus, name="substitution_plan_status"), nullable=False, default=SubstitutionPlanStatus.PROPOSED
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SubstitutionAssignment(UUIDPKMixin, TimestampMixin, Base):
    """One row per AffectedLesson in the plan -- either a chosen substitute
    (ASSIGNED) or a documented reason nothing could be assigned
    (UNFILLED). Acadex never invents a cover teacher just to fill the row.
    """

    __tablename__ = "substitution_assignments"
    __table_args__ = (UniqueConstraint("substitution_plan_id", "affected_lesson_id", name="uq_assignment_plan_lesson"),)

    substitution_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("substitution_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    affected_lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("affected_lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[AssignmentStatus] = mapped_column(Enum(AssignmentStatus, name="substitution_assignment_status"), nullable=False)
    substitute_teacher_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class TimetableException(UUIDPKMixin, TimestampMixin, Base):
    """An approved, dated override of a single TimetableEntry -- the normal
    timetable is never modified or overwritten. A null
    substitute_teacher_user_id means the lesson was approved as
    genuinely uncovered (self-study / merged / cancelled at the school's
    discretion), still recorded so the day's history is accurate.
    """

    __tablename__ = "timetable_exceptions"

    school_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    timetable_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("timetable_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    substitute_teacher_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    substitution_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("substitution_plans.id", ondelete="SET NULL"), nullable=True
    )


class Notification(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
