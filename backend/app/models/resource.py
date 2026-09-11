import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.models.planner_class import YearGroup


class ResourceType(str, PyEnum):
    EXAM_SPECIFICATION = "exam_specification"
    SCHEME_OF_WORK = "scheme_of_work"
    TEACHER_NOTES = "teacher_notes"
    LESSON_RESOURCE = "lesson_resource"
    WORKSHEET = "worksheet"
    PAST_PAPER = "past_paper"
    MARK_SCHEME = "mark_scheme"
    PRACTICAL_GUIDE = "practical_guide"
    CURRICULUM_DOCUMENT = "curriculum_document"
    OTHER = "other"


class ResourceVisibility(str, PyEnum):
    """PRIVATE is invisible to everyone but the uploader -- including a school
    owner/admin. This is what the brief means by "the school administrator
    should NOT automatically have permission to access private teacher
    resources": a teacher opts a resource into that, it isn't the default
    silently applied to protect against oversight failing to notice a leak
    -- ORGANIZATION (shared with the workspace) is the default, matching a
    school resource library being the primary use case.
    """

    PRIVATE = "private"
    ORGANIZATION = "organization"


class ExtractionStatus(str, PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class Resource(UUIDPKMixin, TimestampMixin, Base):
    """Metadata is teacher-filled at upload time, never inferred -- see
    docs/LESSON_PLANNER_ARCHITECTURE.md section 9. subject_name/
    exam_board_name/qualification are free text, matching TeachingClass, for
    the same reason: no FK into the student platform's GCSE/IAL-only Subject
    taxonomy, which has nothing for Early Years/KS1/KS2.
    """

    __tablename__ = "resources"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    resource_type: Mapped[ResourceType] = mapped_column(Enum(ResourceType, name="resource_type"), nullable=False)
    visibility: Mapped[ResourceVisibility] = mapped_column(
        Enum(ResourceVisibility, name="resource_visibility"), default=ResourceVisibility.ORGANIZATION, nullable=False
    )

    subject_name: Mapped[str | None] = mapped_column(String(120))
    exam_board_name: Mapped[str | None] = mapped_column(String(120))
    qualification: Mapped[str | None] = mapped_column(String(100))
    year_group: Mapped[YearGroup | None] = mapped_column(Enum(YearGroup, name="year_group"))
    topic: Mapped[str | None] = mapped_column(String(200))
    unit: Mapped[str | None] = mapped_column(String(200))
    source: Mapped[str | None] = mapped_column(String(200))

    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        Enum(ExtractionStatus, name="resource_extraction_status"), default=ExtractionStatus.PENDING, nullable=False
    )
    extraction_error: Mapped[str | None] = mapped_column(Text)


class ResourceChunk(UUIDPKMixin, Base):
    __tablename__ = "resource_chunks"

    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
