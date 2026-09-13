import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    password_fingerprint,
    verify_password,
)
from app.models.school import School, SchoolMembership, SchoolMembershipRole
from app.models.user import SchoolAdminProfile, TeacherProfile, User, UserRole
from app.schemas.auth import SchoolRegisterRequest, SchoolSummary, TeacherRegisterRequest
from app.services.school_service import get_membership_for_user


def get_display_name(db: Session, user: User) -> str:
    if user.role == UserRole.TEACHER:
        profile = db.query(TeacherProfile).filter_by(user_id=user.id).first()
    else:
        profile = db.query(SchoolAdminProfile).filter_by(user_id=user.id).first()
    return profile.display_name if profile else user.email


def get_school_summary(db: Session, user: User) -> SchoolSummary | None:
    membership = get_membership_for_user(db, user)
    if not membership:
        return None
    school = db.get(School, membership.school_id)
    return SchoolSummary(id=school.id, name=school.name, my_role=membership.role.value)


def _issue_tokens(db: Session, user: User) -> dict:
    return {
        "access_token": create_access_token(user.id, user.role.value),
        "refresh_token": create_refresh_token(user.id),
        "user": {"id": user.id, "email": user.email, "role": user.role, "display_name": get_display_name(db, user)},
        "school": get_school_summary(db, user),
    }


def register_teacher(db: Session, payload: TeacherRegisterRequest) -> dict:
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")

    user = User(email=payload.email, hashed_password=hash_password(payload.password), role=UserRole.TEACHER, is_active=True)
    db.add(user)
    db.flush()
    db.add(TeacherProfile(user_id=user.id, display_name=payload.display_name))
    db.commit()
    db.refresh(user)
    return _issue_tokens(db, user)


def register_school(db: Session, payload: SchoolRegisterRequest) -> dict:
    if db.query(User).filter(User.email == payload.admin_email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")

    admin = User(
        email=payload.admin_email,
        hashed_password=hash_password(payload.admin_password),
        role=UserRole.SCHOOL_ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.flush()
    db.add(SchoolAdminProfile(user_id=admin.id, display_name=payload.admin_display_name))

    school = School(name=payload.school_name, created_by_user_id=admin.id)
    db.add(school)
    db.flush()
    db.add(SchoolMembership(school_id=school.id, user_id=admin.id, role=SchoolMembershipRole.ADMIN))

    db.commit()
    db.refresh(admin)
    return _issue_tokens(db, admin)


def authenticate(db: Session, email: str, password: str) -> dict:
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active or not verify_password(password, user.hashed_password):
        raise invalid
    return _issue_tokens(db, user)


def request_password_reset(db: Session, email: str) -> str | None:
    """Always returns the same generic outcome to the caller regardless of
    whether the email exists (see the endpoint) -- the token itself is only
    returned to the *caller of this function*, and only ever surfaced in
    the HTTP response outside production (no email backend exists yet).
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    token = create_password_reset_token(user.id, user.hashed_password)
    return token if get_settings().environment != "production" else None


def reset_password(db: Session, token: str, new_password: str) -> None:
    claims = decode_token(token)
    if not claims or claims.get("purpose") != "password_reset":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired.")

    user = db.query(User).filter(User.id == uuid.UUID(claims["sub"])).first()
    if not user or claims.get("pwd_fp") != password_fingerprint(user.hashed_password):
        # The fingerprint mismatches if the password already changed since
        # this token was issued -- treat that exactly like an expired token.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired.")

    user.hashed_password = hash_password(new_password)
    db.commit()
