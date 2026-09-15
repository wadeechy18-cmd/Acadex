import uuid
from enum import Enum as PyEnum

from sqlalchemy import BigInteger, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class ResourceKind(str, PyEnum):
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    IMAGE = "image"
    TEXT = "text"


class ExtractionStatus(str, PyEnum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


CONTENT_TYPE_TO_KIND = {
    "application/pdf": ResourceKind.PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ResourceKind.DOCX,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ResourceKind.PPTX,
    "text/plain": ResourceKind.TEXT,
    "image/jpeg": ResourceKind.IMAGE,
    "image/png": ResourceKind.IMAGE,
    "image/webp": ResourceKind.IMAGE,
    "image/gif": ResourceKind.IMAGE,
}


class Resource(UUIDPKMixin, TimestampMixin, Base):
    """A file a teacher has uploaded to reuse when generating lesson plans.
    Scoped to its uploader only for now -- school-wide shared resources
    (see the School product's "Resources" sidebar item) are a later,
    additive extension (a nullable school_id column), not part of this
    shape yet.

    subject_id/year_group_id are optional tags a teacher can set at upload
    (or later) so the resource-first retrieval in
    app/planning/resource_matching.py can narrow the library before falling
    back to a text-overlap search -- untagged resources are still
    searchable, just less precisely.
    """

    __tablename__ = "resources"

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(150), nullable=False)
    kind: Mapped[ResourceKind] = mapped_column(Enum(ResourceKind, name="resource_kind"), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        Enum(ExtractionStatus, name="resource_extraction_status"), nullable=False, default=ExtractionStatus.PENDING
    )
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    year_group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("year_groups.id", ondelete="SET NULL"), nullable=True, index=True
    )
