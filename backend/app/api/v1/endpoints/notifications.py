import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import NotificationResponse
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/mine", response_model=list[NotificationResponse])
def list_my_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[NotificationResponse]:
    return notification_service.list_my_notifications(db, user)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_read(notification_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> NotificationResponse:
    return notification_service.mark_read(db, user, notification_id)
