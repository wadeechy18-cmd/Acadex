import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    actor_name: str
    action: str
    target_type: str
    target_id: uuid.UUID
    summary: str
    created_at: datetime
