import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class Class(UUIDPKMixin, TimestampMixin, Base):
    """A teacher's own class group (e.g. "Year 7A"). Student rosters and
    timetable linkage are later, additive extensions -- not part of this
    shape yet; for now a class is just something a lesson plan can be
    assigned to and something tasks can reference.
    """

    __tablename__ = "classes"

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=True)
    year_group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("year_groups.id"), nullable=True)
