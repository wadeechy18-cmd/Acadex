import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.organization import OrganizationRole
from app.models.user import User, UserRole
from app.schemas.organization import (
    MemberAdd,
    MemberRoleUpdate,
    OrganizationCreate,
    OrganizationMemberResponse,
    OrganizationResponse,
)
from app.services import organization_service
from app.services.auth_service import get_display_name

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/me", response_model=list[OrganizationResponse])
def my_organizations(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[OrganizationResponse]:
    if user.role == UserRole.TEACHER:
        # Lazily backfills a personal workspace for teachers who existed before
        # this feature shipped — new teachers already get one at registration.
        organization_service.get_or_create_personal_organization(db, user)

    rows = organization_service.list_user_organizations(db, user)
    return [
        OrganizationResponse(id=org.id, kind=org.kind, name=org.name, created_at=org.created_at, my_role=role)
        for org, role in rows
    ]


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> OrganizationResponse:
    org = organization_service.create_school_organization(db, user, payload.name)
    return OrganizationResponse(
        id=org.id, kind=org.kind, name=org.name, created_at=org.created_at, my_role=OrganizationRole.OWNER
    )


@router.get("/{organization_id}/members", response_model=list[OrganizationMemberResponse])
def get_members(
    organization_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[OrganizationMemberResponse]:
    members = organization_service.list_members(db, user, organization_id)
    rows = []
    for member in members:
        member_user = db.get(User, member.user_id)
        rows.append(
            OrganizationMemberResponse(
                id=member.id,
                user_id=member.user_id,
                email=member_user.email if member_user else "",
                display_name=get_display_name(db, member_user) if member_user else "",
                role=member.role,
                joined_at=member.joined_at,
            )
        )
    return rows


@router.post("/{organization_id}/members", response_model=OrganizationMemberResponse, status_code=status.HTTP_201_CREATED)
def invite_member(
    organization_id: uuid.UUID,
    payload: MemberAdd,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrganizationMemberResponse:
    member = organization_service.add_member(db, user, organization_id, payload.email, payload.role)
    member_user = db.get(User, member.user_id)
    return OrganizationMemberResponse(
        id=member.id,
        user_id=member.user_id,
        email=member_user.email,
        display_name=get_display_name(db, member_user),
        role=member.role,
        joined_at=member.joined_at,
    )


@router.patch("/{organization_id}/members/{member_id}", response_model=OrganizationMemberResponse)
def change_member_role(
    organization_id: uuid.UUID,
    member_id: uuid.UUID,
    payload: MemberRoleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrganizationMemberResponse:
    member = organization_service.update_member_role(db, user, organization_id, member_id, payload.role)
    member_user = db.get(User, member.user_id)
    return OrganizationMemberResponse(
        id=member.id,
        user_id=member.user_id,
        email=member_user.email,
        display_name=get_display_name(db, member_user),
        role=member.role,
        joined_at=member.joined_at,
    )


@router.delete("/{organization_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    organization_id: uuid.UUID,
    member_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    organization_service.remove_member(db, user, organization_id, member_id)
