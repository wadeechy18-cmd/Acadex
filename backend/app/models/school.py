import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class SchoolMembershipRole(str, PyEnum):
    """A teacher's standing *within one school* -- separate from the
    account-level UserRole. ADMIN here means "has admin rights in this
    school", held by the User who registered it (role=SCHOOL_ADMIN) or
    anyone they promote; TEACHER means an ordinary teaching member.
    """

    ADMIN = "admin"
    TEACHER = "teacher"


class School(UUIDPKMixin, TimestampMixin, Base):
    """A real, isolated tenant -- never a teacher's own account standing in
    for one. Every school-scoped row (classes, lesson plans, timetable,
    tasks, ...) carries a school_id FK back to this table, and every
    school-scoped query must go through assert_school_member() (see
    app/services/school_service.py) before touching it.
    """

    __tablename__ = "schools"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class SchoolMembership(UUIDPKMixin, Base):
    __tablename__ = "school_memberships"
    __table_args__ = (UniqueConstraint("school_id", "user_id", name="uq_school_membership"),)

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[SchoolMembershipRole] = mapped_column(
        Enum(SchoolMembershipRole, name="school_membership_role"), nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
