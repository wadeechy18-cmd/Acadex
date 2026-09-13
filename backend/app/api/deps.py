import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_error

    claims = decode_token(token)
    if not claims or claims.get("purpose") != "access":
        raise credentials_error

    user = db.query(User).filter(User.id == uuid.UUID(claims["sub"])).first()
    if not user or not user.is_active:
        raise credentials_error

    return user


def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User | None:
    if not token:
        return None
    claims = decode_token(token)
    if not claims or claims.get("purpose") != "access":
        return None
    user = db.query(User).filter(User.id == uuid.UUID(claims["sub"])).first()
    return user if user and user.is_active else None


def require_roles(*roles: UserRole):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action.")
        return user

    return dependency


require_teacher = require_roles(UserRole.TEACHER)
require_school_admin = require_roles(UserRole.SCHOOL_ADMIN)
