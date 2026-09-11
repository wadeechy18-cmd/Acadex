import uuid

from sqlalchemy.orm import Session

from app.models.activity import ActivityLog
from app.models.organization import OrganizationRole
from app.models.user import User
from app.services.auth_service import get_display_name
from app.services.organization_service import assert_org_member

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


def log_activity(
    db: Session, *, organization_id: uuid.UUID, user_id: uuid.UUID, action: str, target_type: str, target_id: uuid.UUID, summary: str
) -> None:
    """Adds the row to the session without committing -- callers already
    commit as part of the write they're logging, so this rides along in the
    same transaction rather than opening a second one.
    """
    db.add(
        ActivityLog(
            organization_id=organization_id,
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            summary=summary[:250],
        )
    )


def list_activity(db: Session, user: User, organization_id: uuid.UUID, limit: int = _DEFAULT_LIMIT) -> list[dict]:
    assert_org_member(db, user, organization_id, min_role=OrganizationRole.ADMIN)
    limit = min(max(limit, 1), _MAX_LIMIT)

    rows = (
        db.query(ActivityLog)
        .filter_by(organization_id=organization_id)
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
        .all()
    )

    results = []
    for row in rows:
        actor = db.get(User, row.user_id) if row.user_id else None
        results.append(
            {
                "id": row.id,
                "user_id": row.user_id,
                "actor_name": get_display_name(db, actor) if actor else "Someone",
                "action": row.action,
                "target_type": row.target_type,
                "target_id": row.target_id,
                "summary": row.summary,
                "created_at": row.created_at,
            }
        )
    return results
