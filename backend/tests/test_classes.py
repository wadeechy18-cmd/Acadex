from tests.conftest import auth_headers, register_teacher


def test_create_list_update_delete_class(client):
    teacher = register_teacher(client)
    headers = auth_headers(teacher)

    create = client.post("/api/v1/classes", json={"name": "Year 7A"}, headers=headers)
    assert create.status_code == 201, create.text
    class_id = create.json()["id"]

    listing = client.get("/api/v1/classes", headers=headers)
    assert len(listing.json()) == 1

    update = client.patch(f"/api/v1/classes/{class_id}", json={"name": "Year 7B"}, headers=headers)
    assert update.status_code == 200
    assert update.json()["name"] == "Year 7B"

    delete = client.delete(f"/api/v1/classes/{class_id}", headers=headers)
    assert delete.status_code == 204
    assert client.get("/api/v1/classes", headers=headers).json() == []


def test_a_teacher_cannot_see_or_modify_another_teachers_class(client):
    owner = register_teacher(client)
    other = register_teacher(client)

    create = client.post("/api/v1/classes", json={"name": "Year 7A"}, headers=auth_headers(owner))
    class_id = create.json()["id"]

    other_headers = auth_headers(other)
    assert client.get("/api/v1/classes", headers=other_headers).json() == []
    assert client.patch(f"/api/v1/classes/{class_id}", json={"name": "x"}, headers=other_headers).status_code == 404
    assert client.delete(f"/api/v1/classes/{class_id}", headers=other_headers).status_code == 404


def test_classes_endpoints_require_authentication(client):
    assert client.get("/api/v1/classes").status_code == 401
