from tests.test_organizations import register_teacher
from tests.conftest import auth_headers


def create_school_class(client) -> tuple[dict, str, str]:
    owner = register_teacher(client, school_name="Lesson Plan School")
    orgs = client.get("/api/v1/organizations/me", headers=auth_headers(owner)).json()
    school_id = next(o["id"] for o in orgs if o["kind"] == "school")
    teaching_class = client.post(
        f"/api/v1/organizations/{school_id}/classes",
        json={"name": "Year 10 Chemistry", "subject_name": "Chemistry", "year_group": "year_10", "qualification": "GCSE"},
        headers=auth_headers(owner),
    ).json()
    return owner, school_id, teaching_class["id"]


def create_lesson_plan(client, owner, class_id, **overrides):
    payload = {
        "title": "Atomic Structure",
        "topic": "Atomic Structure",
        "duration_minutes": 50,
        "template_type": "standard",
        **overrides,
    }
    res = client.post(f"/api/v1/classes/{class_id}/lesson-plans", json=payload, headers=auth_headers(owner))
    assert res.status_code == 201, res.text
    return res.json()


def test_create_lesson_plan_starts_at_version_1_with_empty_content(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)
    assert plan["latest_version_number"] == 1
    assert plan["status"] == "draft"

    detail = client.get(f"/api/v1/lesson-plans/{plan['id']}", headers=auth_headers(owner)).json()
    assert detail["content"]["sections"] == []
    assert detail["content"]["learning_objectives"] == []


def test_only_class_owner_can_create_lesson_plan(client):
    owner, school_id, class_id = create_school_class(client)
    other_teacher = register_teacher(client)
    client.post(
        f"/api/v1/organizations/{school_id}/members",
        json={"email": other_teacher["email"], "role": "teacher"},
        headers=auth_headers(owner),
    )

    res = client.post(
        f"/api/v1/classes/{class_id}/lesson-plans",
        json={"title": "Hijack", "topic": "x", "duration_minutes": 50},
        headers=auth_headers(other_teacher),
    )
    assert res.status_code == 403


def test_save_content_creates_new_version_and_preserves_old_ones(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    content_v2 = {
        "content": {
            "learning_objectives": ["Explain the structure of the atom"],
            "sections": [
                {"id": "s1", "type": "starter", "title": "Retrieval quiz", "duration_minutes": 5, "body": []},
                {
                    "id": "s2",
                    "type": "teacher_input",
                    "title": "Explaining atomic structure",
                    "duration_minutes": 15,
                    "body": [{"type": "paragraph", "text": "Protons, neutrons, electrons..."}],
                },
            ],
        }
    }
    save = client.put(f"/api/v1/lesson-plans/{plan['id']}/content", json=content_v2, headers=auth_headers(owner))
    assert save.status_code == 200
    assert save.json()["version_number"] == 2

    detail = client.get(f"/api/v1/lesson-plans/{plan['id']}", headers=auth_headers(owner)).json()
    assert detail["latest_version_number"] == 2
    assert len(detail["content"]["sections"]) == 2
    assert detail["content"]["learning_objectives"] == ["Explain the structure of the atom"]

    versions = client.get(f"/api/v1/lesson-plans/{plan['id']}/versions", headers=auth_headers(owner)).json()
    assert [v["version_number"] for v in versions] == [2, 1]


def test_restore_version_appends_rather_than_deletes_history(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    client.put(
        f"/api/v1/lesson-plans/{plan['id']}/content",
        json={"content": {"learning_objectives": ["v2 objective"]}},
        headers=auth_headers(owner),
    )
    versions = client.get(f"/api/v1/lesson-plans/{plan['id']}/versions", headers=auth_headers(owner)).json()
    v1_id = next(v["id"] for v in versions if v["version_number"] == 1)

    restore = client.post(
        f"/api/v1/lesson-plans/{plan['id']}/versions/{v1_id}/restore", headers=auth_headers(owner)
    )
    assert restore.status_code == 200
    assert restore.json()["version_number"] == 3

    detail = client.get(f"/api/v1/lesson-plans/{plan['id']}", headers=auth_headers(owner)).json()
    assert detail["content"]["learning_objectives"] == []  # back to v1's (empty) content
    assert detail["latest_version_number"] == 3

    versions_after = client.get(f"/api/v1/lesson-plans/{plan['id']}/versions", headers=auth_headers(owner)).json()
    assert len(versions_after) == 3  # nothing was deleted


def test_duplicate_creates_independent_copy_owned_by_caller(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)
    client.put(
        f"/api/v1/lesson-plans/{plan['id']}/content",
        json={"content": {"learning_objectives": ["original objective"]}},
        headers=auth_headers(owner),
    )

    dup = client.post(f"/api/v1/lesson-plans/{plan['id']}/duplicate", headers=auth_headers(owner))
    assert dup.status_code == 201
    copy = dup.json()
    assert copy["id"] != plan["id"]
    assert copy["title"] == "Atomic Structure (Copy)"
    assert copy["latest_version_number"] == 1

    copy_detail = client.get(f"/api/v1/lesson-plans/{copy['id']}", headers=auth_headers(owner)).json()
    assert copy_detail["content"]["learning_objectives"] == ["original objective"]

    # Editing the copy must not affect the original.
    client.put(
        f"/api/v1/lesson-plans/{copy['id']}/content",
        json={"content": {"learning_objectives": ["changed in copy only"]}},
        headers=auth_headers(owner),
    )
    original_after = client.get(f"/api/v1/lesson-plans/{plan['id']}", headers=auth_headers(owner)).json()
    assert original_after["content"]["learning_objectives"] == ["original objective"]


def test_school_admin_can_view_but_not_edit_or_save_content(client):
    owner, school_id, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    teacher = register_teacher(client)
    client.post(
        f"/api/v1/organizations/{school_id}/members",
        json={"email": teacher["email"], "role": "teacher"},
        headers=auth_headers(owner),
    )

    # Owner (school admin) can view the teacher's... wait, this plan belongs
    # to the owner themselves; the interesting case is the reverse: the
    # member teacher (not the plan's author) trying to edit the owner's plan.
    view = client.get(f"/api/v1/lesson-plans/{plan['id']}", headers=auth_headers(teacher))
    assert view.status_code == 200

    edit_attempt = client.patch(
        f"/api/v1/lesson-plans/{plan['id']}", json={"title": "Hijacked"}, headers=auth_headers(teacher)
    )
    assert edit_attempt.status_code == 403

    save_attempt = client.put(
        f"/api/v1/lesson-plans/{plan['id']}/content",
        json={"content": {"learning_objectives": ["hijack"]}},
        headers=auth_headers(teacher),
    )
    assert save_attempt.status_code == 403


def test_non_member_cannot_view_lesson_plan(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)
    outsider = register_teacher(client)

    res = client.get(f"/api/v1/lesson-plans/{plan['id']}", headers=auth_headers(outsider))
    assert res.status_code == 403


def test_owner_can_delete_own_plan(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    res = client.delete(f"/api/v1/lesson-plans/{plan['id']}", headers=auth_headers(owner))
    assert res.status_code == 204

    res_after = client.get(f"/api/v1/lesson-plans/{plan['id']}", headers=auth_headers(owner))
    assert res_after.status_code == 404
