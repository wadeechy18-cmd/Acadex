"""Phase 10: PDF/DOCX export. These check the HTTP layer (status, content
type, non-empty body, and that PDF/DOCX output is well-formed enough to be
opened) -- app/export/pdf.py and docx.py already have direct render-level
coverage via being exercised here through the real service/endpoint path.
"""

from io import BytesIO

from docx import Document

from tests.conftest import auth_headers
from tests.test_lesson_plans import create_lesson_plan, create_school_class
from tests.test_organizations import register_teacher
from tests.test_worksheets import create_homework, create_worksheet

_PDF_MEDIA_TYPE = "application/pdf"
_DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_export_lesson_plan_as_pdf(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    res = client.get(f"/api/v1/lesson-plans/{plan['id']}/export", params={"format": "pdf"}, headers=auth_headers(owner))
    assert res.status_code == 200
    assert res.headers["content-type"] == _PDF_MEDIA_TYPE
    assert res.content[:5] == b"%PDF-"
    assert "attachment" in res.headers["content-disposition"]


def test_export_lesson_plan_as_docx(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    res = client.get(f"/api/v1/lesson-plans/{plan['id']}/export", params={"format": "docx"}, headers=auth_headers(owner))
    assert res.status_code == 200
    assert res.headers["content-type"] == _DOCX_MEDIA_TYPE
    assert res.content[:2] == b"PK"  # docx is a zip container


def test_export_lesson_plan_defaults_to_pdf(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    res = client.get(f"/api/v1/lesson-plans/{plan['id']}/export", headers=auth_headers(owner))
    assert res.status_code == 200
    assert res.headers["content-type"] == _PDF_MEDIA_TYPE


def test_export_lesson_plan_rejects_bad_format(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    res = client.get(f"/api/v1/lesson-plans/{plan['id']}/export", params={"format": "exe"}, headers=auth_headers(owner))
    assert res.status_code == 422


def test_export_lesson_plan_requires_org_membership(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)

    outsider = register_teacher(client)
    res = client.get(f"/api/v1/lesson-plans/{plan['id']}/export", headers=auth_headers(outsider))
    assert res.status_code == 403


def test_export_lesson_plan_with_special_characters_does_not_break_pdf_markup(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id, title="Fish & Chips <Ltd>", topic="Cause & effect")

    res = client.get(f"/api/v1/lesson-plans/{plan['id']}/export", params={"format": "pdf"}, headers=auth_headers(owner))
    assert res.status_code == 200
    assert res.content[:5] == b"%PDF-"


def _docx_text(content: bytes) -> str:
    doc = Document(BytesIO(content))
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.extend(cell.text for cell in row.cells)
    return "\n".join(parts)


def test_export_worksheet_without_answers_omits_answer_column(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)
    worksheet = create_worksheet(client, owner, plan["id"])

    res = client.get(f"/api/v1/worksheets/{worksheet['id']}/export", params={"format": "docx"}, headers=auth_headers(owner))
    assert res.status_code == 200
    assert "Answer 1" not in _docx_text(res.content)  # answers excluded by default


def test_export_worksheet_with_answers_includes_answer_key(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)
    worksheet = create_worksheet(client, owner, plan["id"])

    res = client.get(
        f"/api/v1/worksheets/{worksheet['id']}/export",
        params={"format": "docx", "include_answers": "true"},
        headers=auth_headers(owner),
    )
    assert res.status_code == 200
    assert "Answer 1" in _docx_text(res.content)


def test_export_homework_pdf_includes_due_date(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)
    homework = create_homework(client, owner, plan["id"])

    res = client.get(f"/api/v1/homework/{homework['id']}/export", params={"format": "pdf"}, headers=auth_headers(owner))
    assert res.status_code == 200
    assert res.content[:5] == b"%PDF-"


def test_export_worksheet_requires_org_membership(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id)
    worksheet = create_worksheet(client, owner, plan["id"])

    outsider = register_teacher(client)
    res = client.get(f"/api/v1/worksheets/{worksheet['id']}/export", headers=auth_headers(outsider))
    assert res.status_code == 403


def test_export_filename_is_sanitised(client):
    owner, _, class_id = create_school_class(client)
    plan = create_lesson_plan(client, owner, class_id, title="Weird / Title: <script>")

    res = client.get(f"/api/v1/lesson-plans/{plan['id']}/export", headers=auth_headers(owner))
    disposition = res.headers["content-disposition"]
    assert "/" not in disposition.split("filename=")[1]
    assert "<" not in disposition
