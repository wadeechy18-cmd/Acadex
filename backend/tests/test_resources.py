import io

from tests.test_organizations import register_teacher
from tests.conftest import auth_headers
from tests.test_text_extraction import make_docx_bytes, make_pdf_bytes


def upload(client, owner, org_id, file_bytes, filename, content_type, **fields):
    data = {"resource_type": "scheme_of_work", **fields}
    files = {"file": (filename, file_bytes, content_type)}
    return client.post(f"/api/v1/organizations/{org_id}/resources", data=data, files=files, headers=auth_headers(owner))


def test_upload_pdf_extracts_and_chunks_text(client):
    owner = register_teacher(client, school_name="Resource School")
    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(owner)).json()
    org_id = next(o["id"] for o in orgs if o["kind"] == "school")

    pdf_bytes = make_pdf_bytes(["GCSE Chemistry scheme of work.", "Term 1: Atomic structure and bonding."])
    res = upload(
        client, owner, org_id, pdf_bytes, "scheme.pdf", "application/pdf",
        subject_name="Chemistry", year_group="year_10", qualification="GCSE",
    )
    assert res.status_code == 201, res.text
    resource = res.json()
    assert resource["extraction_status"] == "completed"
    assert resource["subject_name"] == "Chemistry"

    chunks = client.get(f"/api/v1/resources/{resource['id']}/chunks", headers=auth_headers(owner)).json()
    assert len(chunks) >= 1
    assert "Atomic structure" in chunks[0]["text"] or any("Atomic structure" in c["text"] for c in chunks)


def test_upload_docx_and_txt_also_work(client):
    owner = register_teacher(client, school_name="Multi Format School")
    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(owner)).json()
    org_id = next(o["id"] for o in orgs if o["kind"] == "school")

    docx_bytes = make_docx_bytes(["Year 4 Maths planning", "Fractions and decimals unit."])
    docx_res = upload(
        client, owner, org_id, docx_bytes, "planning.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        subject_name="Mathematics", year_group="year_4",
    )
    assert docx_res.status_code == 201
    assert docx_res.json()["extraction_status"] == "completed"

    txt_res = upload(client, owner, org_id, b"Plain teacher notes about phonics.", "notes.txt", "text/plain", subject_name="Phonics")
    assert txt_res.status_code == 201
    assert txt_res.json()["extraction_status"] == "completed"


def test_upload_rejects_unsupported_file_type(client):
    owner = register_teacher(client, school_name="Reject School")
    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(owner)).json()
    org_id = next(o["id"] for o in orgs if o["kind"] == "school")

    res = upload(client, owner, org_id, b"fake image data", "photo.png", "image/png")
    assert res.status_code == 400


def test_corrupt_pdf_upload_stores_failed_status_not_a_500(client):
    owner = register_teacher(client, school_name="Corrupt School")
    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(owner)).json()
    org_id = next(o["id"] for o in orgs if o["kind"] == "school")

    res = upload(client, owner, org_id, b"this is not a real pdf file", "broken.pdf", "application/pdf")
    assert res.status_code == 201  # upload itself succeeds -- extraction failure is recorded, not fatal
    resource = res.json()
    assert resource["extraction_status"] == "failed"
    assert resource["extraction_error"]

    chunks = client.get(f"/api/v1/resources/{resource['id']}/chunks", headers=auth_headers(owner)).json()
    assert chunks == []


def test_private_resource_invisible_to_other_org_members(client):
    owner = register_teacher(client, school_name="Privacy School")
    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(owner)).json()
    org_id = next(o["id"] for o in orgs if o["kind"] == "school")

    teacher = register_teacher(client)
    client.post(f"/api/v1/organizations/{org_id}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(owner))

    private_res = upload(client, owner, org_id, b"private notes", "private.txt", "text/plain", visibility="private")
    resource_id = private_res.json()["id"]

    # Owner (uploader) can see it.
    assert client.get(f"/api/v1/resources/{resource_id}", headers=auth_headers(owner)).status_code == 200

    # Fellow org member -- even though they share the school -- gets a 404, not a 403
    # (confirming a private resource exists at all is itself information to withhold).
    other_view = client.get(f"/api/v1/resources/{resource_id}", headers=auth_headers(teacher))
    assert other_view.status_code == 404

    listing = client.get(f"/api/v1/organizations/{org_id}/resources", headers=auth_headers(teacher)).json()
    assert all(r["id"] != resource_id for r in listing)

    # But it does show up in the owner's own listing.
    owner_listing = client.get(f"/api/v1/organizations/{org_id}/resources", headers=auth_headers(owner)).json()
    assert any(r["id"] == resource_id for r in owner_listing)


def test_organization_visible_resource_shown_to_all_members(client):
    owner = register_teacher(client, school_name="Shared School")
    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(owner)).json()
    org_id = next(o["id"] for o in orgs if o["kind"] == "school")

    teacher = register_teacher(client)
    client.post(f"/api/v1/organizations/{org_id}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(owner))

    shared_res = upload(client, owner, org_id, b"shared notes", "shared.txt", "text/plain")  # default visibility
    resource_id = shared_res.json()["id"]

    assert client.get(f"/api/v1/resources/{resource_id}", headers=auth_headers(teacher)).status_code == 200


def test_non_member_cannot_upload_or_view(client):
    owner = register_teacher(client, school_name="Outsider School")
    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(owner)).json()
    org_id = next(o["id"] for o in orgs if o["kind"] == "school")
    outsider = register_teacher(client)

    upload_attempt = upload(client, outsider, org_id, b"x", "x.txt", "text/plain")
    assert upload_attempt.status_code == 403

    list_attempt = client.get(f"/api/v1/organizations/{org_id}/resources", headers=auth_headers(outsider))
    assert list_attempt.status_code == 403


def test_only_uploader_can_delete_shared_resource(client):
    owner = register_teacher(client, school_name="Delete School")
    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(owner)).json()
    org_id = next(o["id"] for o in orgs if o["kind"] == "school")

    teacher = register_teacher(client)
    client.post(f"/api/v1/organizations/{org_id}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(owner))

    res = upload(client, teacher, org_id, b"teachers own notes", "own.txt", "text/plain")
    resource_id = res.json()["id"]

    delete_by_owner = client.delete(f"/api/v1/resources/{resource_id}", headers=auth_headers(owner))
    assert delete_by_owner.status_code == 403

    delete_by_uploader = client.delete(f"/api/v1/resources/{resource_id}", headers=auth_headers(teacher))
    assert delete_by_uploader.status_code == 204


def test_filter_resources_by_subject_and_year_group(client):
    owner = register_teacher(client, school_name="Filter School")
    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(owner)).json()
    org_id = next(o["id"] for o in orgs if o["kind"] == "school")

    upload(client, owner, org_id, b"maths content", "maths.txt", "text/plain", subject_name="Mathematics", year_group="year_4")
    upload(client, owner, org_id, b"science content", "science.txt", "text/plain", subject_name="Science", year_group="year_6")

    maths_only = client.get(f"/api/v1/organizations/{org_id}/resources?subject_name=Math", headers=auth_headers(owner)).json()
    assert len(maths_only) == 1
    assert maths_only[0]["subject_name"] == "Mathematics"

    year_6_only = client.get(f"/api/v1/organizations/{org_id}/resources?year_group=year_6", headers=auth_headers(owner)).json()
    assert len(year_6_only) == 1
    assert year_6_only[0]["subject_name"] == "Science"
