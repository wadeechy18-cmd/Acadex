import uuid
from enum import Enum as PyEnum

from sqlalchemy import Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class PastPaperSession(str, PyEnum):
    JANUARY = "january"
    MAY_JUNE = "may_june"
    OCTOBER_NOVEMBER = "october_november"


class PastPaperResourceType(str, PyEnum):
    OFFICIAL_LINK = "official_link"
    LICENSED_DOCUMENT = "licensed_document"
    ORIGINAL_SOLUTION = "original_solution"


class PastPaper(UUIDPKMixin, TimestampMixin, Base):
    """Metadata only. Actual documents are stored/linked only when Acadex has the
    legal right to host or link to them — see PastPaperResource. This model never
    stores scraped copyrighted exam content itself.
    """

    __tablename__ = "past_papers"
    __table_args__ = (
        UniqueConstraint(
            "subject_id", "year", "session", "paper_number", name="uq_past_paper_identity"
        ),
    )

    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exam_board_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exam_boards.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    session: Mapped[PastPaperSession] = mapped_column(Enum(PastPaperSession, name="past_paper_session"), nullable=False)
    paper_number: Mapped[str] = mapped_column(String(20), nullable=False)

    resources: Mapped[list["PastPaperResource"]] = relationship(
        back_populates="past_paper", cascade="all, delete-orphan"
    )
    paper_questions: Mapped[list["PastPaperQuestion"]] = relationship(
        back_populates="past_paper", cascade="all, delete-orphan"
    )


class PastPaperResource(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "past_paper_resources"

    past_paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("past_papers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resource_type: Mapped[PastPaperResourceType] = mapped_column(
        Enum(PastPaperResourceType, name="past_paper_resource_type"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    external_url: Mapped[str | None] = mapped_column(String(1000))
    storage_key: Mapped[str | None] = mapped_column(String(500))

    past_paper: Mapped["PastPaper"] = relationship(back_populates="resources")


class PastPaperQuestion(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "past_paper_questions"

    past_paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("past_papers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    question_number: Mapped[str] = mapped_column(String(20), nullable=False)
    marks: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    past_paper: Mapped["PastPaper"] = relationship(back_populates="paper_questions")
