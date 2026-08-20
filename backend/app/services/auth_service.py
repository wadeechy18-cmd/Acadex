import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    password_fingerprint,
    verify_password,
)
from app.models.user import AdminProfile, StudentProfile, TeacherProfile, User, UserRole
from app.schemas.auth import RegisterRequest


def get_display_name(db: Session, user: User) -> str:
    if user.role == UserRole.STUDENT:
        profile = db.query(StudentProfile).filter_by(user_id=user.id).first()
    elif user.role == UserRole.TEACHER:
        profile = db.query(TeacherProfile).filter_by(user_id=user.id).first()
    else:
        profile = db.query(AdminProfile).filter_by(user_id=user.id).first()
    return profile.display_name if profile else user.email


def register_user(db: Session, payload: RegisterRequest) -> User:
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    if payload.role == UserRole.STUDENT:
        db.add(StudentProfile(user_id=user.id, display_name=payload.display_name))
    elif payload.role == UserRole.TEACHER:
        db.add(TeacherProfile(user_id=user.id, display_name=payload.display_name, is_verified_teacher=False))

    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated.")
    return user


def issue_tokens(user: User) -> tuple[str, str]:
    return create_access_token(user.id, user.role.value), create_refresh_token(user.id)


def refresh_access_token(db: Session, refresh_token: str) -> tuple[str, str]:
    claims = decode_token(refresh_token)
    if not claims or claims.get("purpose") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token.")

    user = db.query(User).filter(User.id == uuid.UUID(claims["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token.")

    return issue_tokens(user)


def request_password_reset(db: Session, email: str) -> str | None:
    """Returns a reset token if the account exists. The caller (endpoint) is
    responsible for delivering it — email delivery is not wired up yet, so in the
    MVP the token is returned directly in the API response for local testing.
    Always return a consistent-shaped response upstream regardless of whether the
    account exists, to avoid leaking which emails are registered.
    """

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    return create_password_reset_token(user.id, user.hashed_password)


def confirm_password_reset(db: Session, token: str, new_password: str) -> None:
    claims = decode_token(token)
    if not claims or claims.get("purpose") != "password_reset":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token.")

    user = db.query(User).filter(User.id == uuid.UUID(claims["sub"])).first()
    if not user or password_fingerprint(user.hashed_password) != claims.get("pwd_fp"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token.")

    user.hashed_password = hash_password(new_password)
    db.commit()
