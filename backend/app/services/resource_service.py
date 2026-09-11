import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.organization import OrganizationRole
from app.models.planner_class import YearGroup
from app.models.resource import ExtractionStatus, Resource, ResourceChunk, ResourceType, ResourceVisibility
from app.models.user import User
from app.planning.text_extraction import TextExtractionError, chunk_text, clean_text, extract_text
from app.services import activity_service
from app.services.organization_service import assert_org_member
from app.storage.base import ALLOWED_DOCUMENT_TYPES, MAX_DOCUMENT_SIZE_BYTES, get_storage_backend

# Truncated in case a parser exception message is unexpectedly long (e.g.
# embeds part of the file) -- this is stored and later shown to the teacher.
_MAX_ERROR_LENGTH = 500

# Keeps a single AI request from ballooning the prompt (and the bill) if a
# teacher selects several large resources -- excerpts, not full documents.
_MAX_RESOURCE_CONTEXT_CHARS = 6000


def upload_resource(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    *,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    resource_type: ResourceType,
    visibility: ResourceVisibility,
    subject_name: str | None,
    exam_board_name: str | None,
    qualification: str | None,
    year_group: YearGroup | None,
    topic: str | None,
    unit: str | None,
    source: str | None,
) -> Resource:
    assert_org_member(db, user, organization_id, min_role=OrganizationRole.TEACHER)

    if content_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported file type: {content_type}")
    if len(file_bytes) > MAX_DOCUMENT_SIZE_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File exceeds the 50MB size limit.")

    storage_key = get_storage_backend().save(file_bytes, filename, content_type, folder="resources")

    resource = Resource(
        organization_id=organization_id,
        uploaded_by_user_id=user.id,
        file_name=filename,
        storage_key=storage_key,
        resource_type=resource_type,
        visibility=visibility,
        subject_name=subject_name,
        exam_board_name=exam_board_name,
        qualification=qualification,
        year_group=year_group,
        topic=topic,
        unit=unit,
        source=source,
        extraction_status=ExtractionStatus.PENDING,
    )
    db.add(resource)
    db.flush()

    try:
        text = clean_text(extract_text(file_bytes, content_type))
        chunks = chunk_text(text) if text else []
        for i, chunk in enumerate(chunks):
            db.add(ResourceChunk(resource_id=resource.id, chunk_index=i, text=chunk))
        resource.extraction_status = ExtractionStatus.COMPLETED
    except TextExtractionError as exc:
        resource.extraction_status = ExtractionStatus.FAILED
        resource.extraction_error = str(exc)[:_MAX_ERROR_LENGTH]

    activity_service.log_activity(
        db,
        organization_id=organization_id,
        user_id=user.id,
        action="resource.uploaded",
        target_type="resource",
        target_id=resource.id,
        summary=resource.file_name,
    )
    db.commit()
    db.refresh(resource)
    return resource


def _visible_to(query, user: User):
    return query.filter(
        (Resource.visibility == ResourceVisibility.ORGANIZATION) | (Resource.uploaded_by_user_id == user.id)
    )


def list_resources(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    *,
    subject_name: str | None = None,
    year_group: YearGroup | None = None,
    topic: str | None = None,
    resource_type: ResourceType | None = None,
) -> list[Resource]:
    assert_org_member(db, user, organization_id)

    query = db.query(Resource).filter_by(organization_id=organization_id)
    query = _visible_to(query, user)
    if subject_name:
        query = query.filter(Resource.subject_name.ilike(f"%{subject_name}%"))
    if year_group:
        query = query.filter(Resource.year_group == year_group)
    if topic:
        query = query.filter(Resource.topic.ilike(f"%{topic}%"))
    if resource_type:
        query = query.filter(Resource.resource_type == resource_type)

    return query.order_by(Resource.created_at.desc()).all()


def get_resource(db: Session, user: User, resource_id: uuid.UUID) -> Resource:
    resource = db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resource not found.")
    assert_org_member(db, user, resource.organization_id)

    if resource.visibility == ResourceVisibility.PRIVATE and resource.uploaded_by_user_id != user.id:
        # Deliberately 404, not 403: confirming a private resource exists at
        # all (even to a fellow org member) leaks more than necessary.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resource not found.")

    return resource


def list_chunks(db: Session, user: User, resource_id: uuid.UUID) -> list[ResourceChunk]:
    get_resource(db, user, resource_id)  # enforces the same visibility rule
    return db.query(ResourceChunk).filter_by(resource_id=resource_id).order_by(ResourceChunk.chunk_index).all()


def build_context_excerpt(db: Session, user: User, resource_ids: list[uuid.UUID]) -> str:
    """Concatenates extracted text from the given resources for use as
    AI prompt context. Reused by every AI-generation entry point (lesson
    plan enhancement, worksheet/homework generation) so they all go through
    the same visibility check and the same size cap.
    """
    parts = []
    for resource_id in resource_ids:
        resource = get_resource(db, user, resource_id)  # enforces visibility -- 404s, never substitutes
        chunks = list_chunks(db, user, resource_id)
        parts.append(f"--- {resource.file_name} ---\n" + "\n".join(c.text for c in chunks))
    return "\n\n".join(parts)[:_MAX_RESOURCE_CONTEXT_CHARS]


def delete_resource(db: Session, user: User, resource_id: uuid.UUID) -> None:
    resource = get_resource(db, user, resource_id)
    if resource.uploaded_by_user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the person who uploaded this resource can delete it.")

    get_storage_backend().delete(resource.storage_key)
    db.delete(resource)
    db.commit()
