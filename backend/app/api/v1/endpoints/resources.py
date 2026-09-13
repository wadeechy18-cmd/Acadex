import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.resource import ResourceKind
from app.models.user import User
from app.schemas.resource import ResourceRenameRequest, ResourceResponse
from app.services import resource_service
from app.storage.base import StorageBackend, get_storage_backend

router = APIRouter(prefix="/resources", tags=["resources"])


@router.post("", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
async def upload_resource(
    file: UploadFile = File(...),
    display_name: str | None = Form(None),
    db: Session = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
    user: User = Depends(get_current_user),
) -> ResourceResponse:
    file_bytes = await file.read()
    return resource_service.upload_resource(
        db, storage, user, file_bytes, file.filename or "upload", file.content_type or "application/octet-stream", display_name
    )


@router.get("", response_model=list[ResourceResponse])
def list_resources(
    kind: ResourceKind | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[ResourceResponse]:
    return resource_service.list_resources(db, user, kind)


@router.patch("/{resource_id}", response_model=ResourceResponse)
def rename_resource(
    resource_id: uuid.UUID, payload: ResourceRenameRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ResourceResponse:
    return resource_service.rename_resource(db, user, resource_id, payload.display_name)


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
    user: User = Depends(get_current_user),
) -> None:
    resource_service.delete_resource(db, storage, user, resource_id)


@router.get("/{resource_id}/file")
def download_resource(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
    user: User = Depends(get_current_user),
) -> Response:
    resource = resource_service.get_owned_resource(db, user, resource_id)
    file_bytes = storage.load(resource.storage_key)
    disposition = "inline" if resource.kind in (ResourceKind.IMAGE, ResourceKind.PDF) else "attachment"
    safe_filename = resource.original_filename.replace("\\", "").replace('"', "").replace("\r", "").replace("\n", "")
    return Response(
        content=file_bytes,
        media_type=resource.content_type,
        headers={"Content-Disposition": f'{disposition}; filename="{safe_filename}"'},
    )
