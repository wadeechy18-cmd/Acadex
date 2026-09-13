import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.school import SchoolMembershipRole


class SchoolMemberAdd(BaseModel):
    email: EmailStr
    role: SchoolMembershipRole = SchoolMembershipRole.TEACHER


class SchoolMemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    display_name: str
    role: SchoolMembershipRole
    joined_at: datetime
