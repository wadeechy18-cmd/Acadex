import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field

from app.models.weekly_plan import DayOfWeek


class WeeklyPlanCreate(BaseModel):
    week_start_date: date  # normalised server-side to that week's Monday


class WeeklyPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    teacher_user_id: uuid.UUID
    week_start_date: date
    created_at: datetime


class WeeklyPlanItemCreate(BaseModel):
    class_id: uuid.UUID
    lesson_plan_id: uuid.UUID | None = None
    day_of_week: DayOfWeek
    start_time: time
    duration_minutes: int = Field(gt=0, le=480)
    topic_override: str | None = Field(default=None, max_length=250)


class WeeklyPlanItemUpdate(BaseModel):
    class_id: uuid.UUID | None = None
    lesson_plan_id: uuid.UUID | None = None
    day_of_week: DayOfWeek | None = None
    start_time: time | None = None
    duration_minutes: int | None = Field(default=None, gt=0, le=480)
    topic_override: str | None = Field(default=None, max_length=250)


class WeeklyPlanItemView(BaseModel):
    """One scheduled session, denormalised for both the API response and as
    the local engine's (app/planning/weekly_planner.py) input -- it never
    touches the ORM or the database, only these plain values.
    """

    id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    lesson_plan_id: uuid.UUID | None
    topic: str | None
    template_type: str | None
    day_of_week: DayOfWeek
    start_time: time
    duration_minutes: int


class WeeklyPlanIssue(BaseModel):
    category: str  # "conflict" | "overload" | "gap" | "repeated_topic" | "missing_assessment"
    severity: str  # "info" | "warning"
    message: str
    day_of_week: DayOfWeek | None = None
    item_ids: list[uuid.UUID] = Field(default_factory=list)


class WeeklyPlanDetail(WeeklyPlanResponse):
    items: list[WeeklyPlanItemView]
    issues: list[WeeklyPlanIssue]
