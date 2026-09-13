import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.lesson_plan_content import LessonPlanContent

styles = getSampleStyleSheet()


def _bullets(items: list[str]):
    return ListFlowable([ListItem(Paragraph(item, styles["Normal"])) for item in items], bulletType="bullet")


def render_lesson_plan_pdf(content: LessonPlanContent, subject_name: str, year_group_name: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    story = []

    story.append(Paragraph(content.title, styles["Title"]))
    story.append(Paragraph(f"{subject_name} · {year_group_name}", styles["Normal"]))
    story.append(Spacer(1, 12))

    def section(heading: str, body):
        story.append(Paragraph(heading, styles["Heading2"]))
        if isinstance(body, list):
            story.append(_bullets(body) if body else Paragraph("-", styles["Normal"]))
        else:
            story.append(Paragraph(body or "-", styles["Normal"]))
        story.append(Spacer(1, 8))

    section("Overview", content.overview)
    section("Learning objectives", content.learning_objectives)
    section("Success criteria", content.success_criteria)
    section("Key vocabulary", content.key_vocabulary)
    section("Prior knowledge", content.prior_knowledge)
    section("Resources needed", content.resources_needed)
    section("Starter", content.starter)
    section("Teacher explanation", content.teacher_explanation)
    section("Guided practice", content.guided_practice)
    section("Independent practice", content.independent_practice)
    section("Key questions", content.key_questions)
    section("Differentiation - Support", content.differentiation.support)
    section("Differentiation - Core", content.differentiation.core)
    section("Differentiation - Greater depth", content.differentiation.greater_depth)
    section("Assessment", content.assessment)
    section("Common misconceptions", content.misconceptions)
    section("Plenary", content.plenary)
    section("Homework", content.homework)
    section("Cross-curricular links", content.cross_curricular_links)

    story.append(Paragraph("Timeline", styles["Heading2"]))
    rows = [["Time", "Activity", "Description"]]
    for entry in content.timeline:
        rows.append([f"{entry.start_minute:02d}-{entry.end_minute:02d}", entry.activity, entry.description])
    table = Table(rows, colWidths=[2.5 * cm, 4 * cm, 10 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dddddd")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(table)

    doc.build(story)
    return buffer.getvalue()
