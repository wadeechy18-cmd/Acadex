import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class OrganizationKind(str, PyEnum):
    """PERSONAL is a private, single-owner workspace auto-created for a teacher
    (individual teacher use case). SCHOOL is a shared workspace multiple
    teachers can belong to. Both use the same organization_members mechanism —
    a personal workspace simply has exactly one member (its owner).
    """

    PERSONAL = "personal"
    SCHOOL = "school"


class OrganizationRole(str, PyEnum):
    """Scoped to one organization only — unrelated to the global User.role
    (student/teacher/admin) used by the rest of the platform. A user can be
    OWNER of their personal workspace and TEACHER in a school at the same time.
    """

    OWNER = "owner"
    ADMIN = "admin"
    TEACHER = "teacher"


class Organization(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    kind: Mapped[OrganizationKind] = mapped_column(Enum(OrganizationKind, name="organization_kind"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    members: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class OrganizationMember(UUIDPKMixin, Base):
    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_organization_member"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[OrganizationRole] = mapped_column(Enum(OrganizationRole, name="organization_role"), nullable=False)
    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="members")
