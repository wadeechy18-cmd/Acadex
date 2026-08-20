import uuid

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: UserRole
    is_active: bool
    is_verified: bool
    display_name: str
