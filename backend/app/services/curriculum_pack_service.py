import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.organization import OrganizationRole
from app.models.resource import Resource, ResourceType, ResourceVisibility
from app.models.user import User
from app.planning.curriculum_pack import get_pack_info, list_packs, render_pack_text
from app.services import resource_service
from app.services.organization_service import assert_org_member

# Tags an imported resource's `source` field so re-importing the same pack
# into the same organization updates/returns that one resource instead of
# piling up duplicates -- a teacher clicking "Import" twice should not end
# up with two copies of the same full-year scheme of work.
_SOURCE_PREFIX = "curriculum_pack:"


def _source_tag(pack_id: str) -> str:
    return f"{_SOURCE_PREFIX}{pack_id}"


def list_packs_with_status(db: Session, user: User, organization_id: uuid.UUID) -> list[dict]:
    assert_org_member(db, user, organization_id)

    imported_sources = {
        r.source
        for r in db.query(Resource.source).filter_by(organization_id=organization_id).all()
        if r.source and r.source.startswith(_SOURCE_PREFIX)
    }

    return [
        {
            "id": pack.id,
            "display_name": pack.display_name,
            "year_group": pack.year_group,
            "already_imported": _source_tag(pack.id) in imported_sources,
        }
        for pack in list_packs()
    ]


def import_pack(db: Session, user: User, organization_id: uuid.UUID, pack_id: str) -> Resource:
    """Idempotent: importing a pack that's already present for this
    organization returns the existing resource rather than duplicating it.
    """
    assert_org_member(db, user, organization_id, min_role=OrganizationRole.TEACHER)

    try:
        pack = get_pack_info(pack_id)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such curriculum pack.")

    existing = db.query(Resource).filter_by(organization_id=organization_id, source=_source_tag(pack_id)).first()
    if existing:
        return existing

    text, _framework_ref = render_pack_text(pack_id)

    return resource_service.upload_resource(
        db,
        user,
        organization_id,
        file_bytes=text.encode("utf-8"),
        filename=f"{pack.display_name}.txt",
        content_type="text/plain",
        resource_type=ResourceType.SCHEME_OF_WORK,
        visibility=ResourceVisibility.ORGANIZATION,
        subject_name=None,
        exam_board_name=None,
        qualification=None,
        year_group=pack.year_group,
        topic="Full year scheme of work",
        unit=None,
        source=_source_tag(pack_id),
    )
