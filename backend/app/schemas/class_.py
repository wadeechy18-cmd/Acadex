import uuid

from pydantic import BaseModel, Field


class ClassCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    subject_id: uuid.UUID | None = None
    year_group_id: uuid.UUID | None = None


class ClassUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    subject_id: uuid.UUID | None = None
    year_group_id: uuid.UUID | None = None


class ClassResponse(BaseModel):
    id: uuid.UUID
    name: str
    subject_id: uuid.UUID | None
    subject_name: str | None
    year_group_id: uuid.UUID | None
    year_group_name: str | None
