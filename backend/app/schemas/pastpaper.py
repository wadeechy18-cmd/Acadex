import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.pastpaper import PastPaperResourceType, PastPaperSession


class PastPaperResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID
    exam_board_id: uuid.UUID | None
    title: str
    year: int
    session: PastPaperSession
    paper_number: str


class PastPaperCreate(BaseModel):
    subject_id: uuid.UUID
    exam_board_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=250)
    year: int = Field(ge=2000, le=2100)
    session: PastPaperSession
    paper_number: str = Field(min_length=1, max_length=20)


class PastPaperResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resource_type: PastPaperResourceType
    label: str
    external_url: str | None
    storage_key: str | None


class PastPaperResourceCreate(BaseModel):
    resource_type: PastPaperResourceType
    label: str = Field(min_length=1, max_length=200)
    external_url: str | None = None


class PastPaperQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question_id: uuid.UUID
    question_number: str
    marks: int


class PastPaperQuestionCreate(BaseModel):
    question_id: uuid.UUID
    question_number: str = Field(min_length=1, max_length=20)
    marks: int = Field(default=1, ge=1)


class PastPaperDetail(PastPaperResponse):
    resources: list[PastPaperResourceResponse]
    paper_questions: list[PastPaperQuestionResponse]
