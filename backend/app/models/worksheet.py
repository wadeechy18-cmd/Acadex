import uuid
from datetime import date

from sqlalchemy import JSON, Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class Worksheet(UUIDPKMixin, TimestampMixin, Base):
    """content is a PracticeSetContent (see app/schemas/worksheet.py) -- a flat
    list of {group, prompt, marks, answer} items, not a subset of the
    existing student-platform Question bank. That bank is scoped to the
    GCSE/IAL/university Subject taxonomy the same way ExamBoard is -- it has
    nothing for Early Years/KS1/KS2, so coupling a worksheet to it would
    make worksheets impossible to build for exactly the classes this project
    was asked to support. group is free text (e.g. "Retrieval", "Knowledge",
    "Application", "Challenge") for the teacher/UI to group by.
    """

    __tablename__ = "worksheets"

    lesson_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lesson_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)


class Homework(UUIDPKMixin, TimestampMixin, Base):
    """Same content shape as Worksheet (group is typically "core"/
    "application"/"challenge" here, matching the brief's homework example)."""

    __tablename__ = "homework"

    lesson_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lesson_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
