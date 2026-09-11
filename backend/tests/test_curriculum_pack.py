"""Phase: bundled starter curriculum packs (EYFS Reception, KS1 Year 1/2) --
real UK National Curriculum-aligned, week-by-week lesson content shipped
with the app, importable into an organization's Resources library exactly
like a teacher-uploaded scheme of work.
"""

from tests.conftest import auth_headers
from tests.test_lesson_plans import create_school_class
from tests.test_organizations import register_teacher


def test_list_curriculum_packs_shows_all_three_unimported(client):
    owner, org_id, _ = create_school_class(client)
    packs = client.get(f"/api/v1/organizations/{org_id}/curriculum-packs", headers=auth_headers(owner)).json()

    assert {p["id"] for p in packs} == {"eyfs", "ks1_y1", "ks1_y2"}
    assert all(not p["already_imported"] for p in packs)


def test_import_eyfs_pack_creates_an_organization_resource(client):
    owner, org_id, _ = create_school_class(client)

    res = client.post(f"/api/v1/organizations/{org_id}/curriculum-packs/eyfs/import", headers=auth_headers(owner))
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["resource_type"] == "scheme_of_work"
    assert body["visibility"] == "organization"
    assert body["year_group"] == "reception"
    assert body["extraction_status"] == "completed"

    listed = client.get(f"/api/v1/organizations/{org_id}/resources", headers=auth_headers(owner)).json()
    assert any(r["id"] == body["id"] for r in listed)


def test_import_ks1_year1_and_year2_packs_use_correct_year_groups(client):
    owner, org_id, _ = create_school_class(client)

    y1 = client.post(f"/api/v1/organizations/{org_id}/curriculum-packs/ks1_y1/import", headers=auth_headers(owner)).json()
    y2 = client.post(f"/api/v1/organizations/{org_id}/curriculum-packs/ks1_y2/import", headers=auth_headers(owner)).json()

    assert y1["year_group"] == "year_1"
    assert y2["year_group"] == "year_2"
    assert y1["id"] != y2["id"]


def test_importing_the_same_pack_twice_is_idempotent(client):
    owner, org_id, _ = create_school_class(client)

    first = client.post(f"/api/v1/organizations/{org_id}/curriculum-packs/eyfs/import", headers=auth_headers(owner)).json()
    second = client.post(f"/api/v1/organizations/{org_id}/curriculum-packs/eyfs/import", headers=auth_headers(owner)).json()
    assert first["id"] == second["id"]

    listed = client.get(f"/api/v1/organizations/{org_id}/resources", headers=auth_headers(owner)).json()
    assert sum(1 for r in listed if r["id"] == first["id"]) == 1


def test_imported_pack_shows_as_already_imported(client):
    owner, org_id, _ = create_school_class(client)
    client.post(f"/api/v1/organizations/{org_id}/curriculum-packs/ks1_y1/import", headers=auth_headers(owner))

    packs = client.get(f"/api/v1/organizations/{org_id}/curriculum-packs", headers=auth_headers(owner)).json()
    by_id = {p["id"]: p for p in packs}
    assert by_id["ks1_y1"]["already_imported"] is True
    assert by_id["ks1_y2"]["already_imported"] is False


def test_import_creates_readable_chunked_content(client):
    owner, org_id, _ = create_school_class(client)
    resource = client.post(f"/api/v1/organizations/{org_id}/curriculum-packs/eyfs/import", headers=auth_headers(owner)).json()

    chunks = client.get(f"/api/v1/resources/{resource['id']}/chunks", headers=auth_headers(owner)).json()
    assert len(chunks) > 1
    all_text = " ".join(c["text"] for c in chunks)
    assert "Personal, Social and Emotional Development" in all_text


def test_import_unknown_pack_404s(client):
    owner, org_id, _ = create_school_class(client)
    res = client.post(f"/api/v1/organizations/{org_id}/curriculum-packs/ks2/import", headers=auth_headers(owner))
    assert res.status_code == 404


def test_curriculum_packs_require_org_membership(client):
    owner, org_id, _ = create_school_class(client)
    outsider = register_teacher(client)

    res = client.get(f"/api/v1/organizations/{org_id}/curriculum-packs", headers=auth_headers(outsider))
    assert res.status_code == 403

    res2 = client.post(f"/api/v1/organizations/{org_id}/curriculum-packs/eyfs/import", headers=auth_headers(outsider))
    assert res2.status_code == 403


def test_imported_resource_is_visible_to_the_whole_organization(client):
    owner, org_id, _ = create_school_class(client)
    colleague = register_teacher(client)
    client.post(
        f"/api/v1/organizations/{org_id}/members", json={"email": colleague["email"], "role": "teacher"}, headers=auth_headers(owner)
    )

    imported = client.post(f"/api/v1/organizations/{org_id}/curriculum-packs/eyfs/import", headers=auth_headers(owner)).json()

    seen_by_colleague = client.get(f"/api/v1/resources/{imported['id']}", headers=auth_headers(colleague))
    assert seen_by_colleague.status_code == 200
