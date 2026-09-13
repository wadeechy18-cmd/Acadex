import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.class_ import Class
from app.models.curriculum import Subject, YearGroup
from app.models.school import SchoolMembership, SchoolMembershipRole
from app.models.user import User
from app.schemas.class_ import ClassCreateRequest, ClassUpdateRequest
from app.services import school_service


def _validate_refs(db: Session, subject_id: uuid.UUID | None, year_group_id: uuid.UUID | None) -> None:
    if subject_id and not db.get(Subject, subject_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found.")
    if year_group_id and not db.get(YearGroup, year_group_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Year group not found.")


def create_class(db: Session, user: User, payload: ClassCreateRequest) -> Class:
    _validate_refs(db, payload.subject_id, payload.year_group_id)
    class_ = Class(owner_user_id=user.id, name=payload.name, subject_id=payload.subject_id, year_group_id=payload.year_group_id)
    db.add(class_)
    db.commit()
    db.refresh(class_)
    return class_


def list_classes(db: Session, user: User) -> list[Class]:
    return db.query(Class).filter_by(owner_user_id=user.id).order_by(Class.name).all()


def list_school_classes(db: Session, actor: User, school_id: uuid.UUID) -> list[Class]:
    """Every class owned by a teacher currently in this school -- Class has
    no school_id column of its own (a teacher belongs to at most one
    school), so this is a join through SchoolMembership rather than a
    direct filter. Read-only, for the school admin's timetable-building
    view; a class itself is still only ever edited by its owning teacher.
    """
    school_service.assert_school_member(db, actor, school_id, min_role=SchoolMembershipRole.ADMIN)
    return (
        db.query(Class)
        .join(SchoolMembership, SchoolMembership.user_id == Class.owner_user_id)
        .filter(SchoolMembership.school_id == school_id)
        .order_by(Class.name)
        .all()
    )


def get_owned_class(db: Session, user: User, class_id: uuid.UUID) -> Class:
    class_ = db.query(Class).filter_by(id=class_id, owner_user_id=user.id).first()
    if not class_:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Class not found.")
    return class_


def update_class(db: Session, user: User, class_id: uuid.UUID, payload: ClassUpdateRequest) -> Class:
    class_ = get_owned_class(db, user, class_id)
    _validate_refs(db, payload.subject_id, payload.year_group_id)
    class_.name = payload.name
    class_.subject_id = payload.subject_id
    class_.year_group_id = payload.year_group_id
    db.commit()
    db.refresh(class_)
    return class_


def delete_class(db: Session, user: User, class_id: uuid.UUID) -> None:
    class_ = get_owned_class(db, user, class_id)
    db.delete(class_)
    db.commit()
