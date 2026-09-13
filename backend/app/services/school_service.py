import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.school import School, SchoolMembership, SchoolMembershipRole
from app.models.user import User, UserRole

_ROLE_RANK = {SchoolMembershipRole.TEACHER: 0, SchoolMembershipRole.ADMIN: 1}


def get_membership(db: Session, user: User, school_id: uuid.UUID) -> SchoolMembership | None:
    return db.query(SchoolMembership).filter_by(school_id=school_id, user_id=user.id).first()


def get_membership_for_user(db: Session, user: User) -> SchoolMembership | None:
    """A teacher belongs to at most one school in v1 -- see school.py's
    module docstring for why SchoolMembership is still a proper join table
    rather than a school_id column on User.
    """
    return db.query(SchoolMembership).filter_by(user_id=user.id).first()


def assert_school_member(
    db: Session, user: User, school_id: uuid.UUID, min_role: SchoolMembershipRole = SchoolMembershipRole.TEACHER
) -> SchoolMembership:
    """The single choke point every school-scoped query must go through --
    this codebase's stand-in for row-level security, since it doesn't use
    Postgres RLS. Never trust a school_id from the client without this.
    """
    membership = get_membership(db, user, school_id)
    if not membership:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not a member of this school.")
    if _ROLE_RANK[membership.role] < _ROLE_RANK[min_role]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action.")
    return membership


def get_school(db: Session, school_id: uuid.UUID) -> School:
    school = db.get(School, school_id)
    if not school:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "School not found.")
    return school


def add_member(db: Session, actor: User, school_id: uuid.UUID, email: str, role: SchoolMembershipRole) -> SchoolMembership:
    assert_school_member(db, actor, school_id, min_role=SchoolMembershipRole.ADMIN)

    target = db.query(User).filter(User.email == email).first()
    if not target:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No teacher account found with that email. Ask them to sign up first, then add them.",
        )
    if target.role != UserRole.TEACHER:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only teacher accounts can be added to a school.")

    if get_membership(db, target, school_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "This person is already a member of this school.")
    if get_membership_for_user(db, target):
        raise HTTPException(status.HTTP_409_CONFLICT, "This teacher already belongs to a different school.")

    member = SchoolMembership(school_id=school_id, user_id=target.id, role=role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def list_members(db: Session, actor: User, school_id: uuid.UUID) -> list[SchoolMembership]:
    assert_school_member(db, actor, school_id)
    return db.query(SchoolMembership).filter_by(school_id=school_id).order_by(SchoolMembership.joined_at).all()


def remove_member(db: Session, actor: User, school_id: uuid.UUID, member_id: uuid.UUID) -> None:
    actor_membership = assert_school_member(db, actor, school_id, min_role=SchoolMembershipRole.ADMIN)

    member = db.query(SchoolMembership).filter_by(id=member_id, school_id=school_id).first()
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found.")

    if member.role == SchoolMembershipRole.ADMIN:
        other_admins = (
            db.query(SchoolMembership)
            .filter(
                SchoolMembership.school_id == school_id,
                SchoolMembership.role == SchoolMembershipRole.ADMIN,
                SchoolMembership.id != member.id,
            )
            .count()
        )
        if other_admins == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "A school must always have at least one admin.")

    db.delete(member)
    db.commit()
