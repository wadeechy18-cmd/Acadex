import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.education import LessonType


class EducationLevelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    order_index: int


class EducationLevelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=120)
    description: str | None = None
    order_index: int = 0


class ExamBoardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    education_level_id: uuid.UUID | None


class ExamBoardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=120)
    education_level_id: uuid.UUID | None = None


class SubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    icon: str | None
    order_index: int
    education_level_id: uuid.UUID
    exam_board_id: uuid.UUID | None


class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=150)
    description: str | None = None
    icon: str | None = None
    order_index: int = 0
    education_level_id: uuid.UUID
    exam_board_id: uuid.UUID | None = None


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID
    title: str
    slug: str
    description: str | None
    is_published: bool
    order_index: int


class CourseCreate(BaseModel):
    subject_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=220)
    description: str | None = None
    order_index: int = 0


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    is_published: bool | None = None


class ChapterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    slug: str
    description: str | None
    order_index: int


class ChapterCreate(BaseModel):
    course_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=220)
    description: str | None = None
    order_index: int = 0


class TopicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chapter_id: uuid.UUID
    title: str
    slug: str
    description: str | None
    order_index: int


class TopicCreate(BaseModel):
    chapter_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=220)
    description: str | None = None
    order_index: int = 0


class LessonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    topic_id: uuid.UUID
    title: str
    slug: str
    lesson_type: LessonType
    order_index: int
    is_published: bool


class LessonCreate(BaseModel):
    topic_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=220)
    lesson_type: LessonType = LessonType.MIXED
    order_index: int = 0


class LessonUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    is_published: bool | None = None


class TopicWithLessons(TopicResponse):
    lessons: list[LessonResponse] = []


class ChapterWithTopics(ChapterResponse):
    topics: list[TopicWithLessons] = []


class CourseDetail(CourseResponse):
    chapters: list[ChapterWithTopics] = []


class SubjectDetail(SubjectResponse):
    courses: list[CourseResponse] = []
