import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.resource import ExtractionStatus, ResourceKind


class ResourceResponse(BaseModel):
    id: uuid.UUID
    display_name: str
    original_filename: str
    content_type: str
    kind: ResourceKind
    file_size_bytes: int
    extraction_status: ExtractionStatus
    extraction_error: str | None
    created_at: datetime
    updated_at: datetime


class ResourceRenameRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
