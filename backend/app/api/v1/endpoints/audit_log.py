import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogResponse
from app.services import audit_service, auth_service

router = APIRouter(prefix="/schools", tags=["audit-log"])


def _to_response(db: Session, entry: AuditLog) -> AuditLogResponse:
    actor = db.get(User, entry.actor_user_id)
    return AuditLogResponse(
        id=entry.id,
        actor_user_id=entry.actor_user_id,
        actor_name=auth_service.get_display_name(db, actor),
        action=entry.action,
        details=entry.details,
        created_at=entry.created_at,
    )


@router.get("/{school_id}/audit-log", response_model=list[AuditLogResponse])
def list_audit_log(school_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[AuditLogResponse]:
    return [_to_response(db, e) for e in audit_service.list_logs(db, user, school_id)]
