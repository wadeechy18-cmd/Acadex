import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.lesson_plan import AbilityLevel, GenerationKind
from app.schemas.lesson_plan_content import LessonPlanContent


class GenerateLessonPlanRequest(BaseModel):
    subject_id: uuid.UUID
    year_group_id: uuid.UUID
    curriculum_topic_id: uuid.UUID | None = None
    topic_title: str | None = Field(default=None, max_length=300)
    duration_minutes: int = Field(ge=5, le=240)
    ability_level: AbilityLevel
    objectives: str | None = None
    instructions: str | None = None
    resource_ids: list[uuid.UUID] = Field(default_factory=list)


class RegenerateSectionRequest(BaseModel):
    instructions: str | None = None


class SaveVersionRequest(BaseModel):
    content: LessonPlanContent


class LessonPlanVersionResponse(BaseModel):
    id: uuid.UUID
    version_number: int
    content: LessonPlanContent
    generation_kind: GenerationKind
    generation_notes: str | None
    safeguarding_flagged: bool
    safeguarding_notes: str | None
    resource_ids: list[uuid.UUID]
    created_at: datetime


class LessonPlanResponse(BaseModel):
    id: uuid.UUID
    subject_id: uuid.UUID
    subject_name: str
    year_group_id: uuid.UUID
    year_group_name: str
    topic_title: str
    duration_minutes: int
    ability_level: AbilityLevel
    created_at: datetime
    current_version: LessonPlanVersionResponse


class LessonPlanSummaryResponse(BaseModel):
    id: uuid.UUID
    subject_name: str
    year_group_name: str
    topic_title: str
    duration_minutes: int
    ability_level: AbilityLevel
    current_version_number: int
    updated_at: datetime
