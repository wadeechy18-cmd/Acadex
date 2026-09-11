"""PDF rendering via reportlab's platypus flowables (not the low-level
canvas) so headings/paragraphs/tables paginate themselves instead of this
module having to lay out coordinates by hand.
"""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.lesson_plan import LessonPlanContent
from app.schemas.worksheet import PracticeSetContent

_styles = getSampleStyleSheet()
_h1, _h2, _h3, _body = _styles["Heading1"], _styles["Heading2"], _styles["Heading3"], _styles["BodyText"]


def _e(text: str) -> str:
    """Escapes user-authored text before handing it to Paragraph(), which
    interprets its input as a small XML/HTML-like markup language -- raw
    "&"/"<"/">" from a teacher's own notes would otherwise break rendering.
    """
    return escape(text)


def _bullets(items: list[str]) -> ListFlowable:
    return ListFlowable([ListItem(Paragraph(_e(i), _body)) for i in items], bulletType="bullet", leftIndent=12)


def render_lesson_plan_pdf(*, title: str, topic: str, duration_minutes: int, content: LessonPlanContent) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    story = [Paragraph(_e(title), _h1), Paragraph(f"{_e(topic)} · {duration_minutes} minutes", _body), Spacer(1, 14)]

    def section(heading: str, items: list[str]) -> None:
        if items:
            story.append(Paragraph(heading, _h2))
            story.append(_bullets(items))
            story.append(Spacer(1, 10))

    section("Learning objectives", content.learning_objectives)
    section("Success criteria", content.success_criteria)
    section("Prior knowledge", content.prior_knowledge)
    section("Key vocabulary", content.key_vocabulary)

    if content.sections:
        story.append(Paragraph("Lesson sections", _h2))
        for s in content.sections:
            story.append(Paragraph(f"{_e(s.title)} ({s.duration_minutes} min)", _h3))
            for block in s.body:
                story.append(Paragraph(_e(block.text), _body))
            story.append(Spacer(1, 6))
        story.append(Spacer(1, 6))

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
            story.append(Paragraph("Differentiation", _h2))
            for label, value in populated:
                story.append(Paragraph(f"<b>{label}:</b> {_e(value)}", _body))
            story.append(Spacer(1, 10))

    section("Assessment for learning", content.assessment_for_learning)
    section("Common misconceptions", content.misconceptions)

    if content.safeguarding_note:
        story.append(Paragraph("Safeguarding note", _h2))
        story.append(Paragraph(_e(content.safeguarding_note), _body))
        story.append(Spacer(1, 10))

    if content.teacher_notes:
        story.append(Paragraph("Teacher notes", _h2))
        story.append(Paragraph(_e(content.teacher_notes), _body))

    doc.build(story)
    return buffer.getvalue()


def render_practice_set_pdf(
    *, title: str, due_date: str | None, content: PracticeSetContent, include_answers: bool
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    story = [Paragraph(_e(title), _h1)]
    if due_date:
        story.append(Paragraph(f"Due: {due_date}", _body))
    if content.instructions:
        story.append(Paragraph(_e(content.instructions), _body))
    story.append(Spacer(1, 12))

    headers = ["#", "Group", "Question", "Marks"] + (["Answer"] if include_answers else [])
    rows = [headers]
    for i, item in enumerate(content.items, start=1):
        row = [str(i), _e(item.group), Paragraph(_e(item.prompt), _body), str(item.marks)]
        if include_answers:
            row.append(Paragraph(_e(item.answer) if item.answer else "", _body))
        rows.append(row)

    if len(rows) > 1:
        table = Table(rows, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        story.append(table)
        total_marks = sum(item.marks for item in content.items)
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"<b>Total marks: {total_marks}</b>", _body))
    else:
        story.append(Paragraph("No items yet.", _body))

    doc.build(story)
    return buffer.getvalue()
