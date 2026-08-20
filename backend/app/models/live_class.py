import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class LiveClassStatus(str, PyEnum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    ENDED = "ended"
    CANCELLED = "cancelled"


class LiveClass(UUIDPKMixin, TimestampMixin, Base):
    """(future) Not exposed via any route/UI in the MVP. Modeled now so the live
    class feature (Section 17 of the product spec) is purely additive later.
    """

    __tablename__ = "live_classes"

    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    max_students: Mapped[int | None] = mapped_column(Integer)
    is_free: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    price_cents: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[LiveClassStatus] = mapped_column(
        Enum(LiveClassStatus, name="live_class_status"), default=LiveClassStatus.SCHEDULED, nullable=False
    )

    enrollments: Mapped[list["LiveClassEnrollment"]] = relationship(
        back_populates="live_class", cascade="all, delete-orphan"
    )
    recording: Mapped["LiveClassRecording | None"] = relationship(
        back_populates="live_class", uselist=False, cascade="all, delete-orphan"
    )


class LiveClassEnrollment(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "live_class_enrollments"

    live_class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("live_classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    live_class: Mapped["LiveClass"] = relationship(back_populates="enrollments")


class LiveClassRecording(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "live_class_recordings"

    live_class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("live_classes.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    live_class: Mapped["LiveClass"] = relationship(back_populates="recording")
