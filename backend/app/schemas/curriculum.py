import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CurriculumSubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    key_stage: str | None = Field(default=None, max_length=20)


class CurriculumSubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    key_stage: str | None
    created_at: datetime
