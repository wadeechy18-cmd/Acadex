import uuid

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.school import SchoolMembershipRole
from app.models.user import User


def log(db: Session, actor: User, school_id: uuid.UUID, action: str, details: dict | None = None) -> None:
    """Fire-and-forget: called after an action has already succeeded, in
    the same transaction as its own commit where practical. Never raises
    on its own account -- an audit trail is a record of what happened, not
    a gate on whether it's allowed to happen.

    No dependency on school_service at module load time (see list_logs'
    deferred import below) so services that both write audit entries and
    are themselves depended on by school_service (e.g. school_service
    itself) don't create an import cycle.
    """
    db.add(AuditLog(school_id=school_id, actor_user_id=actor.id, action=action, details=details or {}))


def list_logs(db: Session, actor: User, school_id: uuid.UUID) -> list[AuditLog]:
    from app.services import school_service

    school_service.assert_school_member(db, actor, school_id, min_role=SchoolMembershipRole.ADMIN)
    return db.query(AuditLog).filter_by(school_id=school_id).order_by(AuditLog.created_at.desc()).limit(500).all()
