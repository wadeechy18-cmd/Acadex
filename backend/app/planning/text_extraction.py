"""Resource-ingestion text pipeline: extract -> clean -> chunk. Pure Python,
no network calls, no AI -- see docs/LESSON_PLANNER_ARCHITECTURE.md section 9.
Every step here only ever reads the uploaded file's text; nothing here
executes or renders the document itself, which matters for a file-parsing
attack surface (see the architecture doc's security notes).
"""

import io
import re

import docx
from pypdf import PdfReader


class TextExtractionError(Exception):
    pass


def extract_text(file_bytes: bytes, content_type: str) -> str:
    try:
        if content_type == "application/pdf":
            return _extract_pdf(file_bytes)
        if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return _extract_docx(file_bytes)
        if content_type == "text/plain":
            return _extract_txt(file_bytes)
    except Exception as exc:  # noqa: BLE001 -- any parser failure becomes a clean, reportable error
        raise TextExtractionError(f"Could not read this file: {exc}") from exc
    raise TextExtractionError(f"Unsupported content type: {content_type}")


def _extract_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(file_bytes: bytes) -> str:
    document = docx.Document(io.BytesIO(file_bytes))
    return "\n\n".join(p.text for p in document.paragraphs if p.text.strip())


def _extract_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="replace")


def clean_text(text: str) -> str:
    """Collapses repeated blank lines and trailing whitespace left over from
    page breaks / running headers-footers, without touching real content.
    """
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned: list[str] = []
    blank_run = 0
    for line in lines:
        if line == "":
            blank_run += 1
            if blank_run > 1:
                continue
        else:
            blank_run = 0
        cleaned.append(line)
    return "\n".join(cleaned).strip()


_PARAGRAPH_SPLIT = re.compile(r"\n{2,}")


def chunk_text(text: str, max_chars: int = 1500) -> list[str]:
    """Section/paragraph-aware chunking: packs whole paragraphs into a chunk
    up to max_chars, only hard-splitting a single paragraph if it alone
    exceeds max_chars. Keeps chunks from cutting a sentence mid-thought where
    avoidable.
    """
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT.split(text) if p.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(paragraph), max_chars):
                chunks.append(paragraph[i : i + max_chars])
            continue

        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > max_chars:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate

    if current:
        chunks.append(current)

    return chunks
