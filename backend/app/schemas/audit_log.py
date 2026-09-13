import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID
    actor_name: str
    action: str
    details: dict
    created_at: datetime
