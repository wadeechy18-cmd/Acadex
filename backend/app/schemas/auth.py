from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole
from app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=1, max_length=120)
    role: UserRole = UserRole.STUDENT

    @field_validator("role")
    @classmethod
    def reject_admin_self_registration(cls, role: UserRole) -> UserRole:
        if role == UserRole.ADMIN:
            raise ValueError("Admin accounts cannot be self-registered.")
        return role


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=72)
