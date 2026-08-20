import uuid
from enum import Enum as PyEnum

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class AIMessageRole(str, PyEnum):
    USER = "user"
    ASSISTANT = "assistant"


class AIConversation(UUIDPKMixin, TimestampMixin, Base):
    """(future) AI tutor conversation. Not wired to any LLM in the MVP — modeled so
    the future AI Tutor / Study Assistant / Practice Generator features (product
    spec Section 19) can be added as a new service + routes without new tables.
    """

    __tablename__ = "ai_conversations"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL")
    )
    question_thread_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("question_threads.id", ondelete="SET NULL")
    )

    messages: Mapped[list["AIMessage"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class AIMessage(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "ai_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[AIMessageRole] = mapped_column(Enum(AIMessageRole, name="ai_message_role"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    question_image_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("question_images.id", ondelete="SET NULL")
    )

    conversation: Mapped["AIConversation"] = relationship(back_populates="messages")
