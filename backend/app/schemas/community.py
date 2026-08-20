from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.community import QuestionThreadStatus, ReportTargetType
from app.models.user import UserRole


class CommentAuthor(BaseModel):
    id: uuid.UUID
    display_name: str
    role: UserRole
    is_verified_teacher: bool = False


class DiscussionCreate(BaseModel):
    topic_id: uuid.UUID
    title: str = Field(min_length=1, max_length=250)


class DiscussionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    topic_id: uuid.UUID | None
    title: str
    created_by_id: uuid.UUID
    created_at: datetime


class CommentCreate(BaseModel):
    discussion_id: uuid.UUID | None = None
    question_thread_id: uuid.UUID | None = None
    parent_comment_id: uuid.UUID | None = None
    body: str = Field(min_length=1, max_length=5000)


class CommentUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    id: uuid.UUID
    body: str
    is_verified_teacher_answer: bool
    is_pinned: bool
    is_deleted: bool
    created_at: datetime
    author: CommentAuthor
    vote_score: int
    my_vote: int | None = None
    replies: list["CommentResponse"] = []


CommentResponse.model_rebuild()


class VoteRequest(BaseModel):
    value: int = Field(ge=-1, le=1)


class QuestionThreadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    subject_id: uuid.UUID
    topic_id: uuid.UUID | None
    description: str | None
    status: QuestionThreadStatus
    created_at: datetime


class QuestionImageResponse(BaseModel):
    id: uuid.UUID
    url: str


class QuestionThreadDetail(QuestionThreadResponse):
    images: list[QuestionImageResponse]
    comments: list[CommentResponse]


class ReportCreate(BaseModel):
    target_type: ReportTargetType
    target_id: uuid.UUID
    reason: str = Field(min_length=1, max_length=1000)
