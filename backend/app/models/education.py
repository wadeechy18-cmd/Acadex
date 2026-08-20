import uuid
from enum import Enum as PyEnum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class LessonType(str, PyEnum):
    VIDEO = "video"
    NOTES = "notes"
    MIXED = "mixed"


class EducationLevel(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "education_levels"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    exam_boards: Mapped[list["ExamBoard"]] = relationship(back_populates="education_level")
    subjects: Mapped[list["Subject"]] = relationship(back_populates="education_level")


class ExamBoard(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "exam_boards"
    __table_args__ = (UniqueConstraint("name", "education_level_id", name="uq_exam_board_level"),)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    education_level_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("education_levels.id", ondelete="CASCADE")
    )

    education_level: Mapped["EducationLevel | None"] = relationship(back_populates="exam_boards")
    subjects: Mapped[list["Subject"]] = relationship(back_populates="exam_board")


class Subject(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "subjects"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(50))
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    education_level_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("education_levels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exam_board_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exam_boards.id", ondelete="SET NULL"), index=True
    )

    education_level: Mapped["EducationLevel"] = relationship(back_populates="subjects")
    exam_board: Mapped["ExamBoard | None"] = relationship(back_populates="subjects")
    courses: Mapped[list["Course"]] = relationship(back_populates="subject", cascade="all, delete-orphan")


class Course(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "courses"

    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_published: Mapped[bool] = mapped_column(default=False, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    subject: Mapped["Subject"] = relationship(back_populates="courses")
    chapters: Mapped[list["Chapter"]] = relationship(back_populates="course", cascade="all, delete-orphan")


class Chapter(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "chapters"

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    course: Mapped["Course"] = relationship(back_populates="chapters")
    topics: Mapped[list["Topic"]] = relationship(back_populates="chapter", cascade="all, delete-orphan")


class Topic(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "topics"

    chapter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    chapter: Mapped["Chapter"] = relationship(back_populates="topics")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="topic", cascade="all, delete-orphan")


class Lesson(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "lessons"

    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    lesson_type: Mapped[LessonType] = mapped_column(Enum(LessonType, name="lesson_type"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(default=False, nullable=False)

    topic: Mapped["Topic"] = relationship(back_populates="lessons")
    video: Mapped["Video | None"] = relationship(back_populates="lesson", uselist=False, cascade="all, delete-orphan")
    notes: Mapped[list["Note"]] = relationship(back_populates="lesson", cascade="all, delete-orphan")
