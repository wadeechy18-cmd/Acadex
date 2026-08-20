import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationResponse

router = APIRouter(tags=["notifications"])


@router.get("/notifications/me", response_model=list[NotificationResponse])
def list_my_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Notification]:
    return db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(50).all()


@router.get("/notifications/me/unread-count")
def unread_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    count = db.query(Notification).filter(Notification.user_id == user.id, Notification.read_at.is_(None)).count()
    return {"count": count}


@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_read(notification_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Notification:
    notification = db.query(Notification).filter_by(id=notification_id, user_id=user.id).first()
    if not notification:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found.")
    if not notification.read_at:
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)
    return notification


@router.post("/notifications/me/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    now = datetime.now(timezone.utc)
    db.query(Notification).filter(Notification.user_id == user.id, Notification.read_at.is_(None)).update({"read_at": now})
    db.commit()
