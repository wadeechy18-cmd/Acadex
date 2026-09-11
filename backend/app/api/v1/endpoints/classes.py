import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.planner_class import TeachingClass
from app.models.user import User
from app.schemas.planner_class import ClassCreate, ClassResponse, ClassUpdate
from app.services import planner_class_service

router = APIRouter(tags=["classes"])


@router.post("/organizations/{organization_id}/classes", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
def create_class(
    organization_id: uuid.UUID,
    payload: ClassCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TeachingClass:
    return planner_class_service.create_class(db, user, organization_id, payload)


@router.get("/organizations/{organization_id}/classes", response_model=list[ClassResponse])
def list_classes(
    organization_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[TeachingClass]:
    return planner_class_service.list_classes(db, user, organization_id)


@router.get("/classes/{class_id}", response_model=ClassResponse)
def get_class(class_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> TeachingClass:
    return planner_class_service.get_class(db, user, class_id)


@router.patch("/classes/{class_id}", response_model=ClassResponse)
def update_class(
    class_id: uuid.UUID, payload: ClassUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> TeachingClass:
    return planner_class_service.update_class(db, user, class_id, payload)


@router.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(class_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    planner_class_service.delete_class(db, user, class_id)
