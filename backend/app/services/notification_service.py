import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.substitution import Notification
from app.models.user import User


def list_my_notifications(db: Session, user: User) -> list[Notification]:
    return db.query(Notification).filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()


def mark_read(db: Session, user: User, notification_id: uuid.UUID) -> Notification:
    notification = db.query(Notification).filter_by(id=notification_id, user_id=user.id).first()
    if not notification:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found.")
    notification.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notification)
    return notification
