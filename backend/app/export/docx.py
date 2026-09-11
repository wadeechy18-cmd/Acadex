"""DOCX rendering via python-docx. No markup-escaping concerns here (unlike
pdf.py) -- python-docx paragraph/cell text is always literal, never parsed
as markup.
"""

from io import BytesIO

from docx import Document

from app.schemas.lesson_plan import LessonPlanContent
from app.schemas.worksheet import PracticeSetContent


def render_lesson_plan_docx(*, title: str, topic: str, duration_minutes: int, content: LessonPlanContent) -> bytes:
    doc = Document()
    doc.add_heading(title, level=1)
    doc.add_paragraph(f"{topic} · {duration_minutes} minutes")

    def section(heading: str, items: list[str]) -> None:
        if items:
            doc.add_heading(heading, level=2)
            for item in items:
                doc.add_paragraph(item, style="List Bullet")

    section("Learning objectives", content.learning_objectives)
    section("Success criteria", content.success_criteria)
    section("Prior knowledge", content.prior_knowledge)
    section("Key vocabulary", content.key_vocabulary)

    if content.sections:
        doc.add_heading("Lesson sections", level=2)
        for s in content.sections:
            doc.add_heading(f"{s.title} ({s.duration_minutes} min)", level=3)
            for block in s.body:
                doc.add_paragraph(block.text)

    if content.differentiation:
        tiers = [
            ("Support", content.differentiation.support),
            ("Core", content.differentiation.core),
            ("Challenge", content.differentiation.challenge),
            ("SEND notes", content.differentiation.send_notes),
            ("EAL notes", content.differentiation.eal_notes),
        ]
        populated = [(label, value) for label, value in tiers if value]
        if populated:
            doc.add_heading("Differentiation", level=2)
            for label, value in populated:
                p = doc.add_paragraph()
                p.add_run(f"{label}: ").bold = True
                p.add_run(value)

    section("Assessment for learning", content.assessment_for_learning)
    section("Common misconceptions", content.misconceptions)

    if content.safeguarding_note:
        doc.add_heading("Safeguarding note", level=2)
        doc.add_paragraph(content.safeguarding_note)

    if content.teacher_notes:
        doc.add_heading("Teacher notes", level=2)
        doc.add_paragraph(content.teacher_notes)

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def render_practice_set_docx(*, title: str, due_date: str | None, content: PracticeSetContent, include_answers: bool) -> bytes:
    doc = Document()
    doc.add_heading(title, level=1)
    if due_date:
        doc.add_paragraph(f"Due: {due_date}")
    if content.instructions:
        doc.add_paragraph(content.instructions)

    if content.items:
        headers = ["#", "Group", "Question", "Marks"] + (["Answer"] if include_answers else [])
        table = doc.add_table(rows=1, cols=len(headers))
        table.style = "Light Grid Accent 1"
        for cell, heading in zip(table.rows[0].cells, headers):
            cell.text = heading
        for i, item in enumerate(content.items, start=1):
            row = table.add_row().cells
            values = [str(i), item.group, item.prompt, str(item.marks)] + ([item.answer or ""] if include_answers else [])
            for cell, value in zip(row, values):
                cell.text = value
        doc.add_paragraph(f"Total marks: {sum(item.marks for item in content.items)}")
    else:
        doc.add_paragraph("No items yet.")

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
