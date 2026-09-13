import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.task import TaskPriority, TaskStatus


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    assigned_to_user_id: uuid.UUID
    subject_id: uuid.UUID | None = None
    class_id: uuid.UUID | None = None
    deadline: date
    priority: TaskPriority = TaskPriority.MEDIUM


class TaskUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    assigned_to_user_id: uuid.UUID
    subject_id: uuid.UUID | None = None
    class_id: uuid.UUID | None = None
    deadline: date
    priority: TaskPriority
    status: TaskStatus


class TaskStatusUpdateRequest(BaseModel):
    status: TaskStatus


class TaskResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    assigned_to_user_id: uuid.UUID
    assigned_to_name: str
    subject_id: uuid.UUID | None
    subject_name: str | None
    class_id: uuid.UUID | None
    class_name: str | None
    deadline: date
    priority: TaskPriority
    status: TaskStatus
    effective_status: str
    created_at: datetime
