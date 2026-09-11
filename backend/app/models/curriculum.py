import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPKMixin


class CurriculumSubject(UUIDPKMixin, Base):
    """A school's own standard list of subject names/key stages, so teachers
    creating classes converge on consistent naming ("Mathematics" vs "Maths")
    instead of each free-typing their own. Deliberately still free text, not
    a link into the existing GCSE/IAL-only Subject table -- same reasoning as
    TeachingClass.subject_name (see planner_class.py): this has to cover
    EYFS/KS1/KS2, which that table doesn't.
    """

    __tablename__ = "curriculum_subjects"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_curriculum_subject_org_name"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    key_stage: Mapped[str | None] = mapped_column(String(20))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
