from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    MeResponse,
    ResetPasswordRequest,
    SchoolRegisterRequest,
    TeacherRegisterRequest,
    UserResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register/teacher", response_model=AuthResponse, status_code=201)
@limiter.limit("10/hour")
def register_teacher(request: Request, payload: TeacherRegisterRequest, db: Session = Depends(get_db)) -> dict:
    return auth_service.register_teacher(db, payload)


@router.post("/register/school", response_model=AuthResponse, status_code=201)
@limiter.limit("10/hour")
def register_school(request: Request, payload: SchoolRegisterRequest, db: Session = Depends(get_db)) -> dict:
    return auth_service.register_school(db, payload)


@router.post("/login", response_model=AuthResponse)
@limiter.limit("20/hour")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    return auth_service.authenticate(db, payload.email, payload.password)


@router.get("/me", response_model=MeResponse)
def me(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        user=UserResponse(id=user.id, email=user.email, role=user.role, display_name=auth_service.get_display_name(db, user)),
        school=auth_service.get_school_summary(db, user),
    )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
@limiter.limit("5/hour")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> ForgotPasswordResponse:
    token = auth_service.request_password_reset(db, payload.email)
    return ForgotPasswordResponse(
        detail="If an account exists with that email, a password reset link has been sent.", reset_token=token
    )


@router.post("/reset-password", status_code=204)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> None:
    auth_service.reset_password(db, payload.token, payload.new_password)
