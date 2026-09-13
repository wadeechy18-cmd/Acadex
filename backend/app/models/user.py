import uuid
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class UserRole(str, PyEnum):
    """The account TYPE, decided once at registration -- distinct from
    SchoolMembership.role, which governs a teacher's standing *within one
    school*. A school admin is never merely a teacher account with extra
    permissions: SCHOOL_ADMIN and TEACHER are different account types from
    the moment of registration (see app/services/auth_service.py). STUDENT
    is reserved for a future phase -- registration never issues it yet.
    """

    SCHOOL_ADMIN = "school_admin"
    TEACHER = "teacher"
    STUDENT = "student"


class User(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TeacherProfile(UUIDPKMixin, TimestampMixin, Base):
    """One-to-one with a TEACHER-role User. Deliberately minimal for now --
    subjects/qualifications/availability/workload live in their own tables
    once the timetable increment introduces them, rather than as loose
    columns here.
    """

    __tablename__ = "teacher_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)


class SchoolAdminProfile(UUIDPKMixin, TimestampMixin, Base):
    """One-to-one with a SCHOOL_ADMIN-role User. A separate table from
    TeacherProfile for the same reason SCHOOL_ADMIN is a separate UserRole:
    a school admin's identity is never a teacher record with a flag on it.
    """

    __tablename__ = "school_admin_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
