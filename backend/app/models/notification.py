import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class NotificationType(str, PyEnum):
    COMMENT_REPLY = "comment_reply"
    TEACHER_ANSWER = "teacher_answer"
    COURSE_UPDATE = "course_update"
    NEW_LESSON = "new_lesson"
    QUIZ_RESULT = "quiz_result"
    TEACHER_ANNOUNCEMENT = "teacher_announcement"


class Notification(UUIDPKMixin, TimestampMixin, Base):
    """In-app notifications only for the MVP. `payload` carries enough context
    (e.g. discussion_id, comment_id) for the frontend to deep-link. Email/push
    delivery can be added later as a background job that reads these rows without
    any schema change.
    """

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType, name="notification_type"), nullable=False)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
