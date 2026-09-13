import io

import pytest

from app.main import app
from app.storage.base import LocalStorageBackend, get_storage_backend
from tests.conftest import auth_headers, register_teacher


@pytest.fixture()
def storage(tmp_path):
    backend = LocalStorageBackend(str(tmp_path), "http://localhost:8000")

    def override():
        return backend

    app.dependency_overrides[get_storage_backend] = override
    yield backend
    del app.dependency_overrides[get_storage_backend]


def _upload_txt(client, headers, filename="notes.txt", content=b"Some lesson notes.", display_name=None):
    data = {"display_name": display_name} if display_name else {}
    return client.post(
        "/api/v1/resources",
        files={"file": (filename, io.BytesIO(content), "text/plain")},
        data=data,
        headers=headers,
    )


def test_upload_list_rename_delete_flow(client, storage):
    teacher = register_teacher(client)
    headers = auth_headers(teacher)

    upload = _upload_txt(client, headers, display_name="My Notes")
    assert upload.status_code == 201, upload.text
    body = upload.json()
    assert body["display_name"] == "My Notes"
    assert body["kind"] == "text"
    assert body["extraction_status"] == "done"
    resource_id = body["id"]

    listing = client.get("/api/v1/resources", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    rename = client.patch(f"/api/v1/resources/{resource_id}", json={"display_name": "Renamed Notes"}, headers=headers)
    assert rename.status_code == 200
    assert rename.json()["display_name"] == "Renamed Notes"

    download = client.get(f"/api/v1/resources/{resource_id}/file", headers=headers)
    assert download.status_code == 200
    assert download.content == b"Some lesson notes."

    delete = client.delete(f"/api/v1/resources/{resource_id}", headers=headers)
    assert delete.status_code == 204

    listing_after = client.get("/api/v1/resources", headers=headers)
    assert listing_after.json() == []


def test_upload_defaults_display_name_to_the_filename(client, storage):
    teacher = register_teacher(client)
    headers = auth_headers(teacher)

    upload = _upload_txt(client, headers, filename="lesson-ideas.txt")
    assert upload.status_code == 201
    assert upload.json()["display_name"] == "lesson-ideas.txt"


def test_unsupported_file_type_is_rejected(client, storage):
    teacher = register_teacher(client)
    headers = auth_headers(teacher)

    res = client.post(
        "/api/v1/resources",
        files={"file": ("archive.zip", io.BytesIO(b"PK\x03\x04"), "application/zip")},
        headers=headers,
    )
    assert res.status_code == 400


def test_a_teacher_cannot_see_rename_download_or_delete_another_teachers_resource(client, storage):
    owner = register_teacher(client)
    other = register_teacher(client)

    upload = _upload_txt(client, auth_headers(owner))
    resource_id = upload.json()["id"]

    other_headers = auth_headers(other)
    assert client.get("/api/v1/resources", headers=other_headers).json() == []
    assert client.patch(f"/api/v1/resources/{resource_id}", json={"display_name": "x"}, headers=other_headers).status_code == 404
    assert client.get(f"/api/v1/resources/{resource_id}/file", headers=other_headers).status_code == 404
    assert client.delete(f"/api/v1/resources/{resource_id}", headers=other_headers).status_code == 404


def test_resource_endpoints_require_authentication(client, storage):
    assert client.get("/api/v1/resources").status_code == 401
