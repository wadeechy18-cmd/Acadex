import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.organization import Organization, OrganizationKind, OrganizationMember, OrganizationRole
from app.models.user import TeacherProfile, User, UserRole

_ROLE_RANK = {OrganizationRole.TEACHER: 0, OrganizationRole.ADMIN: 1, OrganizationRole.OWNER: 2}


def get_or_create_personal_organization(db: Session, user: User) -> Organization:
    """Every teacher gets exactly one PERSONAL organization, created lazily the
    first time they touch the planner (existing teachers) or eagerly at
    registration (new teachers — see auth_service.register_user). Idempotent.
    """
    existing = (
        db.query(Organization)
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .filter(
            OrganizationMember.user_id == user.id,
            Organization.kind == OrganizationKind.PERSONAL,
        )
        .first()
    )
    if existing:
        return existing

    org = Organization(kind=OrganizationKind.PERSONAL, name="My Workspace", created_by_user_id=user.id)
    db.add(org)
    db.flush()
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role=OrganizationRole.OWNER))
    db.commit()
    db.refresh(org)
    return org


def create_school_organization(db: Session, user: User, name: str) -> Organization:
    org = Organization(kind=OrganizationKind.SCHOOL, name=name, created_by_user_id=user.id)
    db.add(org)
    db.flush()
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role=OrganizationRole.OWNER))
    db.commit()
    db.refresh(org)
    return org


def list_user_organizations(db: Session, user: User) -> list[tuple[Organization, OrganizationRole]]:
    rows = (
        db.query(Organization, OrganizationMember.role)
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .filter(OrganizationMember.user_id == user.id)
        .order_by(Organization.created_at)
        .all()
    )
    return [(org, role) for org, role in rows]


def get_membership(db: Session, user: User, organization_id: uuid.UUID) -> OrganizationMember | None:
    return (
        db.query(OrganizationMember)
        .filter_by(organization_id=organization_id, user_id=user.id)
        .first()
    )


def assert_org_member(
    db: Session, user: User, organization_id: uuid.UUID, min_role: OrganizationRole = OrganizationRole.TEACHER
) -> OrganizationMember:
    """The single choke point every planner query must go through before
    touching any row scoped to `organization_id`. Never trust organization_id
    from the client without this check — this is the server-side isolation
    boundary standing in for the RLS the codebase doesn't otherwise use.
    """
    membership = get_membership(db, user, organization_id)
    if not membership:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not a member of this organization.")
    if _ROLE_RANK[membership.role] < _ROLE_RANK[min_role]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action.")
    return membership


def add_member(db: Session, actor: User, organization_id: uuid.UUID, email: str, role: OrganizationRole) -> OrganizationMember:
    actor_membership = assert_org_member(db, actor, organization_id, min_role=OrganizationRole.ADMIN)
    if _ROLE_RANK[role] > _ROLE_RANK[actor_membership.role]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot grant a role higher than your own.")

    target = db.query(User).filter(User.email == email).first()
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No account found with that email.")
    if target.role != UserRole.TEACHER:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only teacher accounts can be added to an organization.")

    existing = get_membership(db, target, organization_id)
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "This person is already a member.")

    member = OrganizationMember(organization_id=organization_id, user_id=target.id, role=role, invited_by_user_id=actor.id)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def update_member_role(
    db: Session, actor: User, organization_id: uuid.UUID, member_id: uuid.UUID, new_role: OrganizationRole
) -> OrganizationMember:
    actor_membership = assert_org_member(db, actor, organization_id, min_role=OrganizationRole.ADMIN)

    member = db.query(OrganizationMember).filter_by(id=member_id, organization_id=organization_id).first()
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found.")

    # An actor can never act on a member ranked above them, nor grant a role
    # above their own -- otherwise an ADMIN could promote themselves (or
    # anyone) straight to OWNER, or demote/remove an existing OWNER.
    if _ROLE_RANK[member.role] > _ROLE_RANK[actor_membership.role]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot modify a member with a higher role than your own.")
    if _ROLE_RANK[new_role] > _ROLE_RANK[actor_membership.role]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot grant a role higher than your own.")

    if member.role == OrganizationRole.OWNER and new_role != OrganizationRole.OWNER:
        other_owners = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.role == OrganizationRole.OWNER,
                OrganizationMember.id != member.id,
            )
            .count()
        )
        if other_owners == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "An organization must always have at least one owner.")

    member.role = new_role
    db.commit()
    db.refresh(member)
    return member


def remove_member(db: Session, actor: User, organization_id: uuid.UUID, member_id: uuid.UUID) -> None:
    actor_membership = assert_org_member(db, actor, organization_id, min_role=OrganizationRole.ADMIN)

    member = db.query(OrganizationMember).filter_by(id=member_id, organization_id=organization_id).first()
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found.")

    if _ROLE_RANK[member.role] > _ROLE_RANK[actor_membership.role]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot remove a member with a higher role than your own.")

    if member.role == OrganizationRole.OWNER:
        other_owners = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.role == OrganizationRole.OWNER,
                OrganizationMember.id != member.id,
            )
            .count()
        )
        if other_owners == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "An organization must always have at least one owner.")

    db.delete(member)
    db.commit()


def list_members(db: Session, actor: User, organization_id: uuid.UUID) -> list[OrganizationMember]:
    assert_org_member(db, actor, organization_id)
    return (
        db.query(OrganizationMember)
        .filter_by(organization_id=organization_id)
        .order_by(OrganizationMember.joined_at)
        .all()
    )
