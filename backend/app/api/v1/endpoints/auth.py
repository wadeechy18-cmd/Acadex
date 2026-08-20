from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import (
    authenticate_user,
    confirm_password_reset,
    get_display_name,
    issue_tokens,
    refresh_access_token,
    register_user,
    request_password_reset,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(db: Session, user: User) -> TokenResponse:
    access_token, refresh_token = issue_tokens(user)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            display_name=get_display_name(db, user),
        ),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = register_user(db, payload)
    return _token_response(db, user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, payload.email, payload.password)
    return _token_response(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(_: User = Depends(get_current_user)) -> None:
    """Access/refresh tokens are stateless JWTs, so logout is enforced client-side
    by discarding both tokens. This endpoint exists for API symmetry and to gate
    behind a valid token (a caller with no valid session can't call it).
    """
    return None


@router.post("/refresh", response_model=RefreshResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> RefreshResponse:
    access_token, refresh_token = refresh_access_token(db, payload.refresh_token)
    return RefreshResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("5/minute")
def password_reset_request(request: Request, payload: PasswordResetRequest, db: Session = Depends(get_db)) -> dict:
    token = request_password_reset(db, payload.email)
    response = {"message": "If an account exists for this email, a reset link has been issued."}
    if token:
        # No email provider is wired up yet (see docs/ARCHITECTURE.md); returning the
        # token directly lets the reset flow be exercised end-to-end in development.
        response["dev_reset_token"] = token
    return response


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
def password_reset_confirm(payload: PasswordResetConfirm, db: Session = Depends(get_db)) -> None:
    confirm_password_reset(db, payload.token, payload.new_password)
    return None


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        display_name=get_display_name(db, user),
    )
