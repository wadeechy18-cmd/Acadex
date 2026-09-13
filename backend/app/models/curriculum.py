import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class Curriculum(UUIDPKMixin, TimestampMixin, Base):
    """A national curriculum, e.g. "English National Curriculum" for
    country="England". Only one exists today, but nothing here assumes
    that -- a second country/curriculum is just another row plus its own
    KeyStage/Subject seed data.
    """

    __tablename__ = "curricula"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)


class KeyStage(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "key_stages"
    __table_args__ = (UniqueConstraint("curriculum_id", "code", name="uq_key_stage_curriculum_code"),)

    curriculum_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class YearGroup(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "year_groups"
    __table_args__ = (UniqueConstraint("key_stage_id", "code", name="uq_year_group_key_stage_code"),)

    key_stage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("key_stages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Subject(UUIDPKMixin, TimestampMixin, Base):
    """A taught subject (Key Stage 1+, e.g. "Mathematics") or, for EYFS, one
    of the seven Areas of Learning (e.g. "Understanding the World") --
    modelled as the same entity so the rest of the hierarchy (and the
    lesson planner form built on top of it) doesn't need to special-case
    EYFS, even though the EYFS framework doesn't itself use the word
    "subject".
    """

    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("curriculum_id", "code", name="uq_subject_curriculum_code"),)

    curriculum_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)


class ProgrammeOfStudy(UUIDPKMixin, TimestampMixin, Base):
    """What a Subject looks like in a specific YearGroup -- the anchor
    point for that subject/year's topics and objectives.
    """

    __tablename__ = "programmes_of_study"
    __table_args__ = (UniqueConstraint("subject_id", "year_group_id", name="uq_pos_subject_year_group"),)

    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("year_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class CurriculumTopic(UUIDPKMixin, TimestampMixin, Base):
    """A unit of teaching within a programme of study (e.g. a half-term's
    theme). This is what the lesson planner's "topic" field and the lesson
    plan library's "filter by topic" search against.
    """

    __tablename__ = "curriculum_topics"

    programme_of_study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programmes_of_study.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Objective(UUIDPKMixin, TimestampMixin, Base):
    """A specific learning objective covered within a topic. The same
    curriculum `code` (e.g. "MATHS.N1") can legitimately recur across
    several topics -- a standard gets revisited over the year -- so
    uniqueness is per-topic, not per-code.
    """

    __tablename__ = "objectives"
    __table_args__ = (UniqueConstraint("curriculum_topic_id", "code", "description", name="uq_objective_topic_code_description"),)

    curriculum_topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("curriculum_topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
