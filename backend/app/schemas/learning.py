import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.learning import BookmarkTargetType, EnrollmentStatus
from app.schemas.education import CourseResponse, TopicResponse


class EnrollmentCreate(BaseModel):
    course_id: uuid.UUID


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    status: EnrollmentStatus
    enrolled_at: datetime


class EnrollmentWithCourse(EnrollmentResponse):
    course: CourseResponse
    completion_percentage: float


class ProgressUpdate(BaseModel):
    completion_percentage: float = Field(ge=0, le=100)
    last_position_seconds: int | None = Field(default=None, ge=0)


class ProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    topic_id: uuid.UUID
    completion_percentage: float
    last_position_seconds: int | None
    completed_at: datetime | None


class ProgressWithTopic(ProgressResponse):
    topic: TopicResponse


class BookmarkCreate(BaseModel):
    target_type: BookmarkTargetType
    target_id: uuid.UUID


class BookmarkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    target_type: BookmarkTargetType
    target_id: uuid.UUID
    created_at: datetime


class DashboardSummary(BaseModel):
    my_courses: list[EnrollmentWithCourse]
    continue_learning: ProgressWithTopic | None
    recent_progress: list[ProgressWithTopic]
    bookmarks: list[BookmarkResponse]
