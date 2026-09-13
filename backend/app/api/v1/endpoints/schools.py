import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.school import SchoolMembership
from app.models.user import User
from app.schemas.school import SchoolMemberAdd, SchoolMemberResponse
from app.services import auth_service, school_service

router = APIRouter(prefix="/schools", tags=["schools"])


def _to_member_response(db: Session, member: SchoolMembership) -> SchoolMemberResponse:
    member_user = db.get(User, member.user_id)
    return SchoolMemberResponse(
        id=member.id,
        user_id=member.user_id,
        email=member_user.email,
        display_name=auth_service.get_display_name(db, member_user),
        role=member.role,
        joined_at=member.joined_at,
    )


@router.get("/{school_id}/members", response_model=list[SchoolMemberResponse])
def list_members(school_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[SchoolMemberResponse]:
    members = school_service.list_members(db, user, school_id)
    return [_to_member_response(db, m) for m in members]


@router.post("/{school_id}/members", response_model=SchoolMemberResponse, status_code=status.HTTP_201_CREATED)
def add_member(
    school_id: uuid.UUID, payload: SchoolMemberAdd, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> SchoolMemberResponse:
    member = school_service.add_member(db, user, school_id, payload.email, payload.role)
    return _to_member_response(db, member)


@router.delete("/{school_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    school_id: uuid.UUID, member_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    school_service.remove_member(db, user, school_id, member_id)
