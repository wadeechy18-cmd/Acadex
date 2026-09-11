import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PracticeItem(BaseModel):
    """One question/task on a worksheet or homework sheet. `group` is
    free-text (e.g. "Retrieval", "Core", "Challenge") so teachers can label
    tiers however their school does -- never a fixed enum, since that varies
    by key stage and subject.
    """

    id: str = Field(min_length=1, max_length=64)
    group: str = Field(min_length=1, max_length=100)
    prompt: str = Field(min_length=1, max_length=4000)
    marks: int = Field(ge=0, le=100)
    answer: str = Field(default="", max_length=4000)


class PracticeSetContent(BaseModel):
    instructions: str | None = Field(default=None, max_length=2000)
    items: list[PracticeItem] = Field(default_factory=list)


class AnswerKeyEntry(BaseModel):
    id: str
    group: str
    prompt: str
    marks: int
    answer: str


class AnswerKey(BaseModel):
    """Derived at read-time from PracticeSetContent, never persisted
    separately -- a stored copy could drift from the questions if a teacher
    edits content without regenerating it.
    """

    total_marks: int
    entries: list[AnswerKeyEntry]


class WorksheetCreate(BaseModel):
    title: str = Field(min_length=1, max_length=250)
    content: PracticeSetContent = Field(default_factory=PracticeSetContent)


class WorksheetUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=250)
    content: PracticeSetContent | None = None


class WorksheetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lesson_plan_id: uuid.UUID
    title: str
    content: PracticeSetContent
    total_marks: int
    estimated_minutes: int
    created_at: datetime
    updated_at: datetime


class WorksheetAIGenerateRequest(BaseModel):
    instructions: str | None = Field(default=None, max_length=2000)
    item_count: int = Field(default=8, ge=1, le=30)
    resource_ids: list[uuid.UUID] = Field(default_factory=list)
