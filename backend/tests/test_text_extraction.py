import io

import docx
from reportlab.pdfgen import canvas

from app.planning.text_extraction import TextExtractionError, chunk_text, clean_text, extract_text


def make_pdf_bytes(text_lines: list[str]) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    y = 800
    for line in text_lines:
        c.drawString(72, y, line)
        y -= 20
    c.save()
    return buffer.getvalue()


def make_docx_bytes(paragraphs: list[str]) -> bytes:
    document = docx.Document()
    for p in paragraphs:
        document.add_paragraph(p)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_extract_text_from_real_pdf():
    pdf_bytes = make_pdf_bytes(["Atomic structure is the study of atoms.", "Protons, neutrons, and electrons."])
    text = extract_text(pdf_bytes, "application/pdf")
    assert "Atomic structure" in text
    assert "Protons" in text


def test_extract_text_from_real_docx():
    docx_bytes = make_docx_bytes(["Scheme of Work: Chemistry", "Week 1: Atomic Structure", "Week 2: Bonding"])
    text = extract_text(docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert "Scheme of Work" in text
    assert "Week 2: Bonding" in text


def test_extract_text_from_plain_text():
    text = extract_text(b"Just some plain notes.\n\nSecond paragraph.", "text/plain")
    assert "Just some plain notes." in text
    assert "Second paragraph." in text


def test_extract_text_rejects_unsupported_type():
    try:
        extract_text(b"whatever", "application/zip")
        assert False, "should have raised"
    except TextExtractionError:
        pass


def test_extract_text_from_corrupt_pdf_raises_clean_error():
    try:
        extract_text(b"not actually a pdf", "application/pdf")
        assert False, "should have raised"
    except TextExtractionError as exc:
        assert "Could not read this file" in str(exc)


def test_clean_text_collapses_repeated_blank_lines():
    raw = "Line one\n\n\n\n\nLine two\n   \nLine three"
    cleaned = clean_text(raw)
    assert "\n\n\n" not in cleaned
    assert "Line one" in cleaned and "Line two" in cleaned and "Line three" in cleaned


def test_chunk_text_packs_paragraphs_without_exceeding_max_chars():
    paragraphs = [f"Paragraph {i}. " + ("word " * 50) for i in range(10)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, max_chars=500)
    assert all(len(c) <= 500 for c in chunks)
    assert sum(len(c) for c in chunks) >= len("".join(paragraphs)) * 0.9  # no large content loss
    # Every paragraph's distinctive marker should survive somewhere in the chunks.
    joined = " ".join(chunks)
    for i in range(10):
        assert f"Paragraph {i}." in joined


def test_chunk_text_hard_splits_a_single_huge_paragraph():
    huge_paragraph = "x" * 5000
    chunks = chunk_text(huge_paragraph, max_chars=1500)
    assert len(chunks) == 4  # 5000 / 1500 rounded up
    assert "".join(chunks) == huge_paragraph


def test_chunk_text_empty_input_returns_no_chunks():
    assert chunk_text("") == []
