import uuid

from pydantic import BaseModel

from app.models.organization import OrganizationRole


class TeacherOverviewRow(BaseModel):
    user_id: uuid.UUID
    display_name: str
    email: str
    role: OrganizationRole
    class_count: int
    lesson_plan_count: int
