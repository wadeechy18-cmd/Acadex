import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.organization import OrganizationKind, OrganizationRole


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: OrganizationKind
    name: str
    created_at: datetime
    my_role: OrganizationRole


class MemberAdd(BaseModel):
    email: str
    role: OrganizationRole = OrganizationRole.TEACHER


class MemberRoleUpdate(BaseModel):
    role: OrganizationRole


class OrganizationMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    display_name: str
    role: OrganizationRole
    joined_at: datetime
