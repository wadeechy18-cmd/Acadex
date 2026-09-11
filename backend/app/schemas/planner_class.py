import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.planner_class import YearGroup


class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    subject_name: str = Field(min_length=1, max_length=120)
    year_group: YearGroup
    qualification: str | None = Field(default=None, max_length=100)
    exam_board_name: str | None = Field(default=None, max_length=120)


class ClassUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    subject_name: str | None = Field(default=None, min_length=1, max_length=120)
    year_group: YearGroup | None = None
    qualification: str | None = Field(default=None, max_length=100)
    exam_board_name: str | None = Field(default=None, max_length=120)


class ClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    teacher_user_id: uuid.UUID
    name: str
    subject_name: str
    year_group: YearGroup
    key_stage: str
    qualification: str | None
    exam_board_name: str | None
