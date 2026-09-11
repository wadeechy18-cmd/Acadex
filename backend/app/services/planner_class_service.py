import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.organization import OrganizationRole
from app.models.planner_class import TeachingClass
from app.models.user import User
from app.schemas.planner_class import ClassCreate, ClassUpdate
from app.services.organization_service import assert_org_member


def create_class(db: Session, user: User, organization_id: uuid.UUID, payload: ClassCreate) -> TeachingClass:
    assert_org_member(db, user, organization_id, min_role=OrganizationRole.TEACHER)

    teaching_class = TeachingClass(
        organization_id=organization_id,
        teacher_user_id=user.id,
        **payload.model_dump(),
    )
    db.add(teaching_class)
    db.commit()
    db.refresh(teaching_class)
    return teaching_class


def list_classes(db: Session, user: User, organization_id: uuid.UUID) -> list[TeachingClass]:
    # Any org member (owner/admin/teacher) can view classes -- a school admin
    # needs this for the weekly/activity overview -- but only the owning
    # teacher can create/edit/delete one (assert_can_manage_class below).
    assert_org_member(db, user, organization_id)
    return (
        db.query(TeachingClass)
        .filter_by(organization_id=organization_id)
        .order_by(TeachingClass.created_at)
        .all()
    )


def get_class(db: Session, user: User, class_id: uuid.UUID) -> TeachingClass:
    teaching_class = db.get(TeachingClass, class_id)
    if not teaching_class:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Class not found.")
    assert_org_member(db, user, teaching_class.organization_id)
    return teaching_class


def assert_can_manage_class(db: Session, user: User, class_id: uuid.UUID) -> TeachingClass:
    """Ownership, not just membership: a school owner/admin can view a class
    (see list_classes) but only the teacher who created it can change it --
    the brief is explicit that a school admin must not create/edit a
    teacher's classes.
    """
    teaching_class = get_class(db, user, class_id)
    if teaching_class.teacher_user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the teacher who owns this class can modify it.")
    return teaching_class


def update_class(db: Session, user: User, class_id: uuid.UUID, payload: ClassUpdate) -> TeachingClass:
    teaching_class = assert_can_manage_class(db, user, class_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(teaching_class, field, value)
    db.commit()
    db.refresh(teaching_class)
    return teaching_class


def delete_class(db: Session, user: User, class_id: uuid.UUID) -> None:
    teaching_class = assert_can_manage_class(db, user, class_id)
    db.delete(teaching_class)
    db.commit()
