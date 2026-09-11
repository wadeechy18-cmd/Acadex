from tests.test_organizations import register_teacher
from tests.conftest import auth_headers


def create_school_and_class(client, class_payload=None) -> tuple[dict, str, dict]:
    owner = register_teacher(client, school_name="Class Test School")
    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(owner)).json()
    school_id = next(o["id"] for o in orgs if o["kind"] == "school")

    payload = class_payload or {
        "name": "Year 10 Chemistry — Set 2",
        "subject_name": "Chemistry",
        "year_group": "year_10",
        "qualification": "GCSE",
        "exam_board_name": "Edexcel",
    }
    res = client.post(f"/api/v1/organizations/{school_id}/classes", json=payload, headers=auth_headers(owner))
    assert res.status_code == 201, res.text
    return owner, school_id, res.json()


def test_create_class_derives_key_stage(client):
    _, _, teaching_class = create_school_and_class(client)
    assert teaching_class["key_stage"] == "KS4"
    assert teaching_class["subject_name"] == "Chemistry"


def test_primary_year_group_maps_to_correct_key_stage(client):
    owner = register_teacher(client, school_name="Primary School")
    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(owner)).json()
    school_id = next(o["id"] for o in orgs if o["kind"] == "school")

    res = client.post(
        f"/api/v1/organizations/{school_id}/classes",
        json={"name": "Year 4 Maths", "subject_name": "Mathematics", "year_group": "year_4"},
        headers=auth_headers(owner),
    )
    assert res.status_code == 201, res.text
    assert res.json()["key_stage"] == "KS2"

    reception = client.post(
        f"/api/v1/organizations/{school_id}/classes",
        json={"name": "Reception phonics", "subject_name": "Phonics", "year_group": "reception"},
        headers=auth_headers(owner),
    )
    assert reception.json()["key_stage"] == "EYFS"


def test_owning_teacher_can_update_and_delete_class(client):
    owner, school_id, teaching_class = create_school_and_class(client)

    update = client.patch(
        f"/api/v1/classes/{teaching_class['id']}", json={"name": "Renamed"}, headers=auth_headers(owner)
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Renamed"

    delete = client.delete(f"/api/v1/classes/{teaching_class['id']}", headers=auth_headers(owner))
    assert delete.status_code == 204


def test_school_admin_can_view_but_not_edit_teachers_class(client):
    owner, school_id, teaching_class = create_school_and_class(client)

    teacher = register_teacher(client)
    client.post(
        f"/api/v1/organizations/{school_id}/members",
        json={"email": teacher["email"], "role": "teacher"},
        headers=auth_headers(owner),
    )
    teacher_class = client.post(
        f"/api/v1/organizations/{school_id}/classes",
        json={"name": "Year 8 Science", "subject_name": "Science", "year_group": "year_8"},
        headers=auth_headers(teacher),
    ).json()

    # Owner (school admin) can list/view classes in their school...
    listing = client.get(f"/api/v1/organizations/{school_id}/classes", headers=auth_headers(owner))
    assert listing.status_code == 200
    assert len(listing.json()) == 2

    # ...but cannot edit or delete a class they don't own.
    edit_attempt = client.patch(
        f"/api/v1/classes/{teacher_class['id']}", json={"name": "Hijacked"}, headers=auth_headers(owner)
    )
    assert edit_attempt.status_code == 403

    delete_attempt = client.delete(f"/api/v1/classes/{teacher_class['id']}", headers=auth_headers(owner))
    assert delete_attempt.status_code == 403


def test_non_member_cannot_create_or_view_classes(client):
    owner, school_id, _ = create_school_and_class(client)
    outsider = register_teacher(client)

    create_attempt = client.post(
        f"/api/v1/organizations/{school_id}/classes",
        json={"name": "Intruder class", "subject_name": "Maths", "year_group": "year_7"},
        headers=auth_headers(outsider),
    )
    assert create_attempt.status_code == 403

    view_attempt = client.get(f"/api/v1/organizations/{school_id}/classes", headers=auth_headers(outsider))
    assert view_attempt.status_code == 403


def test_class_in_personal_workspace_isolated_from_school(client):
    """A teacher's personal-workspace class must be invisible to a school
    they also belong to.
    """
    school_owner = register_teacher(client, school_name="Boundary School")
    teacher = register_teacher(client)

    school_orgs = client.get("/api/v1/organizations/me", headers=auth_headers(school_owner)).json()
    school_id = next(o["id"] for o in school_orgs if o["kind"] == "school")
    client.post(
        f"/api/v1/organizations/{school_id}/members",
        json={"email": teacher["email"], "role": "teacher"},
        headers=auth_headers(school_owner),
    )

    teacher_orgs = client.get("/api/v1/organizations/me", headers=auth_headers(teacher)).json()
    personal_id = next(o["id"] for o in teacher_orgs if o["kind"] == "personal")

    personal_class = client.post(
        f"/api/v1/organizations/{personal_id}/classes",
        json={"name": "My private tutoring group", "subject_name": "Maths", "year_group": "year_9"},
        headers=auth_headers(teacher),
    ).json()

    # School owner has no access to the teacher's personal workspace class at all.
    res = client.get(f"/api/v1/classes/{personal_class['id']}", headers=auth_headers(school_owner))
    assert res.status_code == 403

    school_classes = client.get(f"/api/v1/organizations/{school_id}/classes", headers=auth_headers(school_owner)).json()
    assert all(c["id"] != personal_class["id"] for c in school_classes)
