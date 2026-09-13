import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: uuid.UUID
    title: str
    body: str
    read_at: datetime | None
    created_at: datetime
