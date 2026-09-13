import uuid

from pydantic import BaseModel


class CurriculumResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    country: str


class KeyStageResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    sort_order: int


class YearGroupResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    sort_order: int


class SubjectResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str


class CurriculumTopicResponse(BaseModel):
    id: uuid.UUID
    title: str
    sort_order: int


class ObjectiveResponse(BaseModel):
    id: uuid.UUID
    code: str
    description: str
