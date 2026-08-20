import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.content import VideoProvider
from app.schemas.education import ChapterResponse, CourseResponse, LessonResponse, SubjectResponse, TopicResponse
from app.schemas.learning import ProgressResponse


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: VideoProvider
    duration_seconds: int | None
    playback_url: str | None = None


class VideoUpsert(BaseModel):
    provider: VideoProvider
    external_id: str | None = None
    storage_key: str | None = None
    thumbnail_key: str | None = None
    duration_seconds: int | None = Field(default=None, ge=0)


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    content_blocks: list[Any]
    order_index: int


class NoteCreate(BaseModel):
    lesson_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    content_blocks: list[Any] = Field(default_factory=list)
    order_index: int = 0


class LessonBreadcrumb(BaseModel):
    topic: TopicResponse
    chapter: ChapterResponse
    course: CourseResponse
    subject: SubjectResponse


class LessonDetail(LessonResponse):
    video: VideoResponse | None
    notes: list[NoteResponse]
    breadcrumb: LessonBreadcrumb
    my_progress: ProgressResponse | None = None
