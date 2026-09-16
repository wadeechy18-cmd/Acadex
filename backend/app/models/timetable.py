import uuid
from datetime import date, time
from enum import Enum as PyEnum

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class AvailabilityStatus(str, PyEnum):
    """A teacher-set baseline preference for a time slot. "Teaching" and
    "Absent" (from the brief's Available/Teaching/Unavailable/Absent list)
    are never stored here -- they're derived at read time (Teaching: has a
    TimetableEntry in that slot; Absent: has a TeacherAbsence for that date,
    added in a later increment), the same pattern as Task's derived
    "overdue" status, so they can never drift out of sync with the actual
    timetable or absence records.
    """

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class AcademicYear(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "academic_years"

    school_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)


class Room(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "rooms"

    school_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)


class TimeSlot(UUIDPKMixin, TimestampMixin, Base):
    """A single named period on a single day (e.g. "Monday Period 1",
    09:00-09:45) -- day-specific rather than a generic period shared
    across days, so a TimetableEntry never needs its own day column.
    """

    __tablename__ = "time_slots"
    __table_args__ = (UniqueConstraint("school_id", "day_of_week", "start_time", "end_time", name="uq_time_slot"),)

    school_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Monday .. 4=Friday
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)


class Timetable(UUIDPKMixin, TimestampMixin, Base):
    """The school's standing weekly timetable for an academic year. Kept
    separate from TimetableException (added when the absence/cover
    increment introduces it) so an emergency substitution day never
    overwrites this normal timetable.
    """

    __tablename__ = "timetables"

    school_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)


class TimetableEntry(UUIDPKMixin, TimestampMixin, Base):
    """One lesson: a teacher teaching a subject to a class in a room during
    a specific time slot on this timetable. Double-booking a teacher,
    class, or room in the same slot is rejected in
    app/services/timetable_service.py, not enforced as a DB constraint,
    since class_id and room_id are optional and a partial unique index
    per nullable column is more trouble than it's worth for the same
    guarantee a service-level check already gives with a clearer error.
    """

    __tablename__ = "timetable_entries"

    timetable_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("timetables.id", ondelete="CASCADE"), nullable=False, index=True)
    time_slot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("time_slots.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=False)
    class_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("classes.id", ondelete="SET NULL"), nullable=True)
    room_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)


class ClassSubjectRequirement(UUIDPKMixin, TimestampMixin, Base):
    """How many periods per week a class needs of a subject on a given
    timetable -- what an admin fills in instead of manually placing every
    lesson; app/planning/timetable_generation.py's CP-SAT solver then fills
    the grid to satisfy as many of these as it can.
    """

    __tablename__ = "class_subject_requirements"
    __table_args__ = (UniqueConstraint("timetable_id", "class_id", "subject_id", name="uq_class_subject_requirement"),)

    timetable_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("timetables.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    periods_per_week: Mapped[int] = mapped_column(Integer, nullable=False)


class TeacherSubjectQualification(UUIDPKMixin, TimestampMixin, Base):
    """Which subjects a teacher is qualified to teach within this school --
    critical for both building the normal timetable and, later, for
    picking a valid substitute during cover assignment.
    """

    __tablename__ = "teacher_subject_qualifications"
    __table_args__ = (UniqueConstraint("school_id", "teacher_user_id", "subject_id", name="uq_teacher_subject_qualification"),)

    school_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)


class TeacherAvailability(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "teacher_availabilities"
    __table_args__ = (UniqueConstraint("school_id", "teacher_user_id", "time_slot_id", name="uq_teacher_availability"),)

    school_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    time_slot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("time_slots.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[AvailabilityStatus] = mapped_column(Enum(AvailabilityStatus, name="teacher_availability_status"), nullable=False)
