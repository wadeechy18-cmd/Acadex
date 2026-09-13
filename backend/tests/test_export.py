import docx
from pypdf import PdfReader

from app.export.docx import render_lesson_plan_docx
from app.export.pdf import render_lesson_plan_pdf
from tests.test_lesson_plans import SAMPLE_CONTENT


def test_export_pdf_contains_the_lesson_title():
    pdf_bytes = render_lesson_plan_pdf(SAMPLE_CONTENT, "Mathematics", "Year 2")
    reader = PdfReader(__import__("io").BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Fractions" in text
    assert "Mathematics" in text


def test_export_docx_contains_all_sections():
    docx_bytes = render_lesson_plan_docx(SAMPLE_CONTENT, "Mathematics", "Year 2")
    document = docx.Document(__import__("io").BytesIO(docx_bytes))
    full_text = "\n".join(p.text for p in document.paragraphs)
    assert SAMPLE_CONTENT.title in full_text
    assert SAMPLE_CONTENT.overview in full_text
    assert SAMPLE_CONTENT.homework in full_text
