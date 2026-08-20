import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum as PyEnum

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

# bcrypt truncates the input silently past 72 bytes; reject longer passwords
# up front instead of hashing a truncated secret.
MAX_PASSWORD_BYTES = 72


class TokenPurpose(str, PyEnum):
    ACCESS = "access"
    REFRESH = "refresh"
    PASSWORD_RESET = "password_reset"


def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes.")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if len(plain_password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return False
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def password_fingerprint(hashed_password: str) -> str:
    """Short fingerprint of the current password hash, embedded in password-reset
    tokens so a token issued before a password change is rejected after one —
    without needing a server-side revocation table.
    """
    return hashlib.sha256(hashed_password.encode()).hexdigest()[:16]


def _create_token(subject: uuid.UUID, purpose: TokenPurpose, expires_delta: timedelta, **extra_claims) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "purpose": purpose.value,
        "iat": now,
        "exp": now + expires_delta,
        **extra_claims,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    return _create_token(
        user_id,
        TokenPurpose.ACCESS,
        timedelta(minutes=settings.access_token_expire_minutes),
        role=role,
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(user_id, TokenPurpose.REFRESH, timedelta(days=settings.refresh_token_expire_days))


def create_password_reset_token(user_id: uuid.UUID, hashed_password: str) -> str:
    return _create_token(
        user_id,
        TokenPurpose.PASSWORD_RESET,
        timedelta(minutes=30),
        pwd_fp=password_fingerprint(hashed_password),
    )


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
