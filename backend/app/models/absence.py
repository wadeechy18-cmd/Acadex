import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class TeacherAbsence(UUIDPKMixin, TimestampMixin, Base):
    """A single teacher's reported absence for one date. Affected lessons
    are computed deterministically (never with AI) from the live
    timetable at report time -- see
    app/services/absence_service.py:report_absence -- and stored as
    AffectedLesson rows so they don't need recomputing on every read.
    """

    __tablename__ = "teacher_absences"

    school_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reported_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)


class AffectedLesson(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "affected_lessons"

    teacher_absence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teacher_absences.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timetable_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("timetable_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
