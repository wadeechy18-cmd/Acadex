import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.class_ import Class
from app.models.curriculum import Subject, YearGroup
from app.models.user import User
from app.schemas.class_ import ClassCreateRequest, ClassResponse, ClassUpdateRequest
from app.services import class_service

router = APIRouter(prefix="/classes", tags=["classes"])


def _to_response(db: Session, class_: Class) -> ClassResponse:
    subject = db.get(Subject, class_.subject_id) if class_.subject_id else None
    year_group = db.get(YearGroup, class_.year_group_id) if class_.year_group_id else None
    return ClassResponse(
        id=class_.id,
        name=class_.name,
        subject_id=class_.subject_id,
        subject_name=subject.name if subject else None,
        year_group_id=class_.year_group_id,
        year_group_name=year_group.name if year_group else None,
    )


@router.post("", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
def create_class(payload: ClassCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ClassResponse:
    class_ = class_service.create_class(db, user, payload)
    return _to_response(db, class_)


@router.get("", response_model=list[ClassResponse])
def list_classes(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ClassResponse]:
    return [_to_response(db, c) for c in class_service.list_classes(db, user)]


@router.patch("/{class_id}", response_model=ClassResponse)
def update_class(
    class_id: uuid.UUID, payload: ClassUpdateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ClassResponse:
    class_ = class_service.update_class(db, user, class_id, payload)
    return _to_response(db, class_)


@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(class_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    class_service.delete_class(db, user, class_id)
