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


def test_school_admin_can_list_classes_owned_by_teachers_in_their_school(client):
    from tests.conftest import register_school

    admin = register_school(client, school_name="Classes Oversight School")
    teacher = register_teacher(client)
    school_id = admin["school"]["id"]
    client.post(f"/api/v1/schools/{school_id}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(admin))

    client.post("/api/v1/classes", json={"name": "Year 3B"}, headers=auth_headers(teacher))

    listing = client.get(f"/api/v1/schools/{school_id}/classes", headers=auth_headers(admin))
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["name"] == "Year 3B"


def test_school_admin_cannot_list_classes_from_another_school(client):
    from tests.conftest import register_school

    admin_a = register_school(client, school_name="Classes School A")
    teacher_a = register_teacher(client)
    school_a = admin_a["school"]["id"]
    client.post(f"/api/v1/schools/{school_a}/members", json={"email": teacher_a["email"], "role": "teacher"}, headers=auth_headers(admin_a))
    client.post("/api/v1/classes", json={"name": "Year 4A"}, headers=auth_headers(teacher_a))

    admin_b = register_school(client, school_name="Classes School B")
    listing = client.get(f"/api/v1/schools/{school_a}/classes", headers=auth_headers(admin_b))
    assert listing.status_code == 403
