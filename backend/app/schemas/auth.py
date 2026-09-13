import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class TeacherRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=1, max_length=200)


class SchoolRegisterRequest(BaseModel):
    school_name: str = Field(min_length=1, max_length=200)
    admin_email: EmailStr
    admin_password: str = Field(min_length=8, max_length=72)
    admin_display_name: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: UserRole
    display_name: str


class SchoolSummary(BaseModel):
    id: uuid.UUID
    name: str
    my_role: str  # "admin" | "teacher"


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserResponse
    school: SchoolSummary | None = None


class MeResponse(BaseModel):
    user: UserResponse
    school: SchoolSummary | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """`reset_token` is only ever populated outside production -- see
    auth_service.request_password_reset. No email backend exists yet, so
    this is how a developer/tester actually completes the flow; production
    behaviour never leaks it here, and the endpoint's response is
    identical whether or not the email exists, so it can't be used to
    enumerate accounts.
    """

    detail: str
    reset_token: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=72)
