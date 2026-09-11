import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.curriculum import CurriculumSubject
from app.models.organization import OrganizationRole
from app.models.user import User
from app.schemas.curriculum import CurriculumSubjectCreate
from app.services.organization_service import assert_org_member


def list_curriculum_subjects(db: Session, user: User, organization_id: uuid.UUID) -> list[CurriculumSubject]:
    # Any member can view the school's standard subject list -- it's a
    # naming-consistency aid for creating classes, not sensitive data.
    assert_org_member(db, user, organization_id)
    return (
        db.query(CurriculumSubject)
        .filter_by(organization_id=organization_id)
        .order_by(CurriculumSubject.name)
        .all()
    )


def create_curriculum_subject(
    db: Session, user: User, organization_id: uuid.UUID, payload: CurriculumSubjectCreate
) -> CurriculumSubject:
    assert_org_member(db, user, organization_id, min_role=OrganizationRole.ADMIN)

    # Checked up front rather than caught as a DB constraint failure: cleaner
    # to reason about, and avoids leaving the session's transaction in a
    # failed state that the caller would need to roll back before reuse.
    existing = (
        db.query(CurriculumSubject)
        .filter(
            CurriculumSubject.organization_id == organization_id,
            func.lower(CurriculumSubject.name) == payload.name.lower(),
        )
        .first()
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "This subject is already on the list.")

    subject = CurriculumSubject(
        organization_id=organization_id, name=payload.name, key_stage=payload.key_stage, created_by_user_id=user.id
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


def delete_curriculum_subject(db: Session, user: User, organization_id: uuid.UUID, subject_id: uuid.UUID) -> None:
    assert_org_member(db, user, organization_id, min_role=OrganizationRole.ADMIN)

    subject = db.query(CurriculumSubject).filter_by(id=subject_id, organization_id=organization_id).first()
    if not subject:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found.")
    db.delete(subject)
    db.commit()
