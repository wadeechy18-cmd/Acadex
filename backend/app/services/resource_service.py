import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.resource import CONTENT_TYPE_TO_KIND, ExtractionStatus, Resource, ResourceKind
from app.models.user import User
from app.planning.text_extraction import TextExtractionError, clean_text, extract_text
from app.storage.base import (
    ALLOWED_DOCUMENT_TYPES,
    ALLOWED_IMAGE_TYPES,
    MAX_DOCUMENT_SIZE_BYTES,
    MAX_IMAGE_SIZE_BYTES,
    StorageBackend,
)

_EXTRACTABLE_KINDS = {ResourceKind.PDF, ResourceKind.DOCX, ResourceKind.PPTX, ResourceKind.TEXT}


def _validate_upload(content_type: str, file_size_bytes: int) -> ResourceKind:
    if content_type in ALLOWED_DOCUMENT_TYPES:
        if file_size_bytes > MAX_DOCUMENT_SIZE_BYTES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is too large (max 50MB for documents).")
    elif content_type in ALLOWED_IMAGE_TYPES:
        if file_size_bytes > MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is too large (max 10MB for images).")
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Unsupported file type. Upload a PDF, Word document, PowerPoint, image, or plain text file.",
        )
    return CONTENT_TYPE_TO_KIND[content_type]


def upload_resource(
    db: Session,
    storage: StorageBackend,
    user: User,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    display_name: str | None,
) -> Resource:
    kind = _validate_upload(content_type, len(file_bytes))
    storage_key = storage.save(file_bytes, filename, content_type, folder=f"resources/{user.id}")

    resource = Resource(
        owner_user_id=user.id,
        display_name=display_name or filename,
        original_filename=filename,
        storage_key=storage_key,
        content_type=content_type,
        kind=kind,
        file_size_bytes=len(file_bytes),
        extraction_status=ExtractionStatus.PENDING if kind in _EXTRACTABLE_KINDS else ExtractionStatus.NOT_APPLICABLE,
    )

    if kind in _EXTRACTABLE_KINDS:
        try:
            resource.extracted_text = clean_text(extract_text(file_bytes, content_type))
            resource.extraction_status = ExtractionStatus.DONE
        except TextExtractionError as exc:
            resource.extraction_status = ExtractionStatus.FAILED
            resource.extraction_error = str(exc)

    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def list_resources(db: Session, user: User, kind: ResourceKind | None = None) -> list[Resource]:
    query = db.query(Resource).filter_by(owner_user_id=user.id)
    if kind:
        query = query.filter_by(kind=kind)
    return query.order_by(Resource.created_at.desc()).all()


def get_owned_resource(db: Session, user: User, resource_id: uuid.UUID) -> Resource:
    # 404 (not 403) whether the resource doesn't exist or belongs to someone
    # else, so a resource id can't be used to probe for other users' files.
    resource = db.query(Resource).filter_by(id=resource_id, owner_user_id=user.id).first()
    if not resource:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resource not found.")
    return resource


def rename_resource(db: Session, user: User, resource_id: uuid.UUID, display_name: str) -> Resource:
    resource = get_owned_resource(db, user, resource_id)
    resource.display_name = display_name
    db.commit()
    db.refresh(resource)
    return resource


def delete_resource(db: Session, storage: StorageBackend, user: User, resource_id: uuid.UUID) -> None:
    resource = get_owned_resource(db, user, resource_id)
    storage.delete(resource.storage_key)
    db.delete(resource)
    db.commit()
