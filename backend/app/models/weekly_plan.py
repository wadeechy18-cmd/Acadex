import uuid
from datetime import date, time
from enum import Enum as PyEnum

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class DayOfWeek(str, PyEnum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class WeeklyPlan(UUIDPKMixin, TimestampMixin, Base):
    """A teacher's own timetable for one calendar week, spanning every class
    they teach in this organization -- not scoped to a single class, so the
    local engine (app/planning/weekly_planner.py) can actually detect
    cross-class problems like double-booking, which is what "overload"
    means for a teacher in practice. week_start_date is always normalised
    to that week's Monday (see weekly_plan_service._monday_of) so there is
    exactly one plan per teacher per organization per ISO week -- every
    teacher has at least a PERSONAL org plus possibly one or more SCHOOL
    orgs, and needs an independent plan in each, so organization_id must be
    part of the uniqueness key, not just (teacher, week).
    """

    __tablename__ = "weekly_plans"
    __table_args__ = (
        UniqueConstraint("organization_id", "teacher_user_id", "week_start_date", name="uq_weekly_plan_org_teacher_week"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    teacher_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    week_start_date: Mapped[date] = mapped_column(Date, nullable=False)


class WeeklyPlanItem(UUIDPKMixin, TimestampMixin, Base):
    """One scheduled session: a class, on a day, at a time, for a duration --
    optionally linked to the actual lesson_plan being taught, or left
    unlinked with a topic_override as a placeholder ("Tuesday period 3,
    9C, fractions -- plan not written yet").
    """

    __tablename__ = "weekly_plan_items"

    weekly_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("weekly_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lesson_plans.id", ondelete="SET NULL"), index=True
    )
    day_of_week: Mapped[DayOfWeek] = mapped_column(Enum(DayOfWeek, name="day_of_week"), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    topic_override: Mapped[str | None] = mapped_column(String(250))
