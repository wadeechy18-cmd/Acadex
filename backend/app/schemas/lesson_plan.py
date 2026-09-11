import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.lesson_plan import LessonPlanStatus, LessonPlanTemplateType


class ContentBlock(BaseModel):
    """Deliberately small today (2 types) -- extend here, not with a free-form
    text field, as the editor grows richer content types.
    """

    type: Literal["paragraph", "activity_instruction"]
    text: str


class DifferentiationNotes(BaseModel):
    """Free-text, teacher-authored tiering -- never a system-inferred
    diagnosis. See docs/LESSON_PLANNER_ARCHITECTURE.md section 14.
    """

    support: str | None = None
    core: str | None = None
    challenge: str | None = None
    send_notes: str | None = None
    eal_notes: str | None = None


class LessonSection(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    type: str = Field(min_length=1, max_length=60)
    title: str = Field(min_length=1, max_length=200)
    duration_minutes: int = Field(ge=0, le=300)
    body: list[ContentBlock] = Field(default_factory=list)


class LessonPlanContent(BaseModel):
    """The whole structured document, versioned as a unit on every save --
    never one giant text blob. Fields the local planning engine (Phase 4)
    and worksheet/homework linkage (Phase 5/7) will add are deliberately
    absent until those tables exist, rather than half-wired now.
    """

    learning_objectives: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    prior_knowledge: list[str] = Field(default_factory=list)
    key_vocabulary: list[str] = Field(default_factory=list)
    sections: list[LessonSection] = Field(default_factory=list)
    differentiation: DifferentiationNotes | None = None
    assessment_for_learning: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    teacher_notes: str | None = None
    safeguarding_note: str | None = None


class LessonPlanCreate(BaseModel):
    title: str = Field(min_length=1, max_length=250)
    topic: str = Field(min_length=1, max_length=250)
    duration_minutes: int = Field(gt=0, le=300)
    template_type: LessonPlanTemplateType = LessonPlanTemplateType.STANDARD


class LessonPlanUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=250)
    topic: str | None = Field(default=None, min_length=1, max_length=250)
    duration_minutes: int | None = Field(default=None, gt=0, le=300)
    template_type: LessonPlanTemplateType | None = None
    status: LessonPlanStatus | None = None


class SaveContentRequest(BaseModel):
    content: LessonPlanContent


class LessonPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    class_id: uuid.UUID
    teacher_user_id: uuid.UUID
    title: str
    topic: str
    duration_minutes: int
    template_type: LessonPlanTemplateType
    status: LessonPlanStatus
    created_at: datetime
    updated_at: datetime
    latest_version_number: int


class LessonPlanDetail(LessonPlanResponse):
    content: LessonPlanContent


class LessonPlanVersionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_number: int
    created_by_user_id: uuid.UUID | None
    created_at: datetime
