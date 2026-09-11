import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.planner_class import YearGroup
from app.models.resource import ExtractionStatus, ResourceType, ResourceVisibility


class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    uploaded_by_user_id: uuid.UUID
    file_name: str
    resource_type: ResourceType
    visibility: ResourceVisibility
    subject_name: str | None
    exam_board_name: str | None
    qualification: str | None
    year_group: YearGroup | None
    topic: str | None
    unit: str | None
    source: str | None
    extraction_status: ExtractionStatus
    extraction_error: str | None
    created_at: datetime


class ResourceChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_index: int
    text: str
