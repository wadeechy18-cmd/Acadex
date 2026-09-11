import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPKMixin


class ActivityLog(UUIDPKMixin, Base):
    """Append-only record of what's been created in an organization, for the
    school admin activity feed (Phase 9). Deliberately logs creation events
    only (a class, lesson plan, resource, worksheet, homework) rather than
    every edit -- a "what's new" feed, not a full edit-history audit trail
    (lesson plans already have their own version history for that).
    """

    __tablename__ = "activity_logs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "class.created"
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "class"
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    summary: Mapped[str] = mapped_column(String(250), nullable=False)  # human-readable, e.g. class/plan title
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
