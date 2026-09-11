import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.planner_class import YearGroup
from app.models.resource import Resource, ResourceChunk, ResourceType, ResourceVisibility
from app.models.user import User
from app.schemas.curriculum_pack import CurriculumPackStatus
from app.schemas.resource import ResourceChunkResponse, ResourceResponse
from app.services import curriculum_pack_service, resource_service

router = APIRouter(tags=["resources"])


@router.post("/organizations/{organization_id}/resources", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
async def upload_resource(
    organization_id: uuid.UUID,
    file: UploadFile = File(...),
    resource_type: ResourceType = Form(...),
    visibility: ResourceVisibility = Form(ResourceVisibility.ORGANIZATION),
    subject_name: str | None = Form(None),
    exam_board_name: str | None = Form(None),
    qualification: str | None = Form(None),
    year_group: YearGroup | None = Form(None),
    topic: str | None = Form(None),
    unit: str | None = Form(None),
    source: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Resource:
    content = await file.read()
    return resource_service.upload_resource(
        db, user, organization_id,
        file_bytes=content, filename=file.filename or "upload", content_type=file.content_type or "application/octet-stream",
        resource_type=resource_type, visibility=visibility,
        subject_name=subject_name, exam_board_name=exam_board_name, qualification=qualification,
        year_group=year_group, topic=topic, unit=unit, source=source,
    )


@router.get("/organizations/{organization_id}/resources", response_model=list[ResourceResponse])
def list_resources(
    organization_id: uuid.UUID,
    subject_name: str | None = None,
    year_group: YearGroup | None = None,
    topic: str | None = None,
    resource_type: ResourceType | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Resource]:
    return resource_service.list_resources(
        db, user, organization_id,
        subject_name=subject_name, year_group=year_group, topic=topic, resource_type=resource_type,
    )


@router.get("/resources/{resource_id}", response_model=ResourceResponse)
def get_resource(resource_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Resource:
    return resource_service.get_resource(db, user, resource_id)


@router.get("/resources/{resource_id}/chunks", response_model=list[ResourceChunkResponse])
def list_chunks(
    resource_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[ResourceChunk]:
    return resource_service.list_chunks(db, user, resource_id)


@router.delete("/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(resource_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    resource_service.delete_resource(db, user, resource_id)


@router.get("/organizations/{organization_id}/curriculum-packs", response_model=list[CurriculumPackStatus])
def list_curriculum_packs(
    organization_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[dict]:
    return curriculum_pack_service.list_packs_with_status(db, user, organization_id)


@router.post(
    "/organizations/{organization_id}/curriculum-packs/{pack_id}/import",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_curriculum_pack(
    organization_id: uuid.UUID, pack_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Resource:
    return curriculum_pack_service.import_pack(db, user, organization_id, pack_id)
