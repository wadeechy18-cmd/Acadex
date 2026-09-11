import uuid
from enum import Enum as PyEnum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class YearGroup(str, PyEnum):
    """Covers the full English education framework, not just secondary —
    Nursery/Reception are Early Years (EYFS), Year 1-2 are KS1, Year 3-6 are
    KS2, Year 7-9 are KS3, Year 10-11 are KS4 (GCSE), Year 12-13 are KS5
    (A-Level/IAL). See key_stage_for_year_group() in planner_class_service.
    """

    NURSERY = "nursery"
    RECEPTION = "reception"
    YEAR_1 = "year_1"
    YEAR_2 = "year_2"
    YEAR_3 = "year_3"
    YEAR_4 = "year_4"
    YEAR_5 = "year_5"
    YEAR_6 = "year_6"
    YEAR_7 = "year_7"
    YEAR_8 = "year_8"
    YEAR_9 = "year_9"
    YEAR_10 = "year_10"
    YEAR_11 = "year_11"
    YEAR_12 = "year_12"
    YEAR_13 = "year_13"


_KEY_STAGE_BY_YEAR_GROUP: dict[YearGroup, str] = {
    YearGroup.NURSERY: "EYFS",
    YearGroup.RECEPTION: "EYFS",
    YearGroup.YEAR_1: "KS1",
    YearGroup.YEAR_2: "KS1",
    YearGroup.YEAR_3: "KS2",
    YearGroup.YEAR_4: "KS2",
    YearGroup.YEAR_5: "KS2",
    YearGroup.YEAR_6: "KS2",
    YearGroup.YEAR_7: "KS3",
    YearGroup.YEAR_8: "KS3",
    YearGroup.YEAR_9: "KS3",
    YearGroup.YEAR_10: "KS4",
    YearGroup.YEAR_11: "KS4",
    YearGroup.YEAR_12: "KS5",
    YearGroup.YEAR_13: "KS5",
}


def key_stage_for_year_group(year_group: YearGroup) -> str:
    return _KEY_STAGE_BY_YEAR_GROUP[year_group]


class TeachingClass(UUIDPKMixin, TimestampMixin, Base):
    """A teacher's class within a workspace (personal or school) -- the unit
    lesson plans, worksheets and homework are organised around. Deliberately
    not named `Class` (a reserved word) or `Course` (already means a
    published, subject-taxonomy-driven piece of student content elsewhere in
    this codebase -- unrelated concept).

    subject_name/exam_board_name are free text, not foreign keys into the
    existing Subject/ExamBoard tables: those tables model the GCSE/IAL/
    university curriculum taxonomy the student platform teaches, which has no
    entries at all for Early Years/KS1/KS2, and coupling a teacher's class to
    it would make primary-school classes impossible to create.
    """

    __tablename__ = "classes"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    teacher_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    subject_name: Mapped[str] = mapped_column(String(120), nullable=False)
    year_group: Mapped[YearGroup] = mapped_column(Enum(YearGroup, name="year_group"), nullable=False)
    qualification: Mapped[str | None] = mapped_column(String(100))
    exam_board_name: Mapped[str | None] = mapped_column(String(120))

    @property
    def key_stage(self) -> str:
        return key_stage_for_year_group(self.year_group)
