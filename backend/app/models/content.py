import uuid
from enum import Enum as PyEnum

from sqlalchemy import Enum, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class VideoProvider(str, PyEnum):
    """External provider that actually hosts/streams the file. The frontend never
    receives a raw provider URL from the DB directly — it resolves through the API,
    which can swap providers without a schema change.
    """

    MUX = "mux"
    CLOUDFLARE_STREAM = "cloudflare_stream"
    YOUTUBE_UNLISTED = "youtube_unlisted"
    S3 = "s3"
    LOCAL = "local"


class Video(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "videos"

    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    provider: Mapped[VideoProvider] = mapped_column(Enum(VideoProvider, name="video_provider"), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255))
    storage_key: Mapped[str | None] = mapped_column(String(500))
    thumbnail_key: Mapped[str | None] = mapped_column(String(500))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="video")


class Note(UUIDPKMixin, TimestampMixin, Base):
    """Rich note content, stored as an ordered list of typed blocks so the frontend
    can render headings, paragraphs, lists, formulas, images, tables, key-point and
    exam-tip callouts consistently and responsively.

    Example `content_blocks` entry:
      {"type": "formula", "latex": "x = \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}"}
      {"type": "exam_tip", "text": "Always check both roots satisfy the original equation."}
    """

    __tablename__ = "notes"

    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_blocks: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="notes")
