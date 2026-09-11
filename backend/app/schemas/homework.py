import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.worksheet import PracticeSetContent, WorksheetAIGenerateRequest


class HomeworkCreate(BaseModel):
    title: str = Field(min_length=1, max_length=250)
    content: PracticeSetContent = Field(default_factory=PracticeSetContent)
    due_date: date | None = None


class HomeworkUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=250)
    content: PracticeSetContent | None = None
    due_date: date | None = None


class HomeworkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lesson_plan_id: uuid.UUID
    title: str
    content: PracticeSetContent
    total_marks: int
    estimated_minutes: int
    due_date: date | None
    created_at: datetime
    updated_at: datetime


class HomeworkAIGenerateRequest(WorksheetAIGenerateRequest):
    pass
