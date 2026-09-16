import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.lesson_plan_content import HomeworkContent, LessonPlanContent, TeacherScriptSection, WorksheetContent

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

    def script_section(heading: str, script: TeacherScriptSection | None, fallback: str):
        """A classroom-ready script prints as labelled lines a teacher can
        read straight off the page; older plans without one fall back to
        the plain summary text.
        """
        story.append(Paragraph(heading, styles["Heading2"]))
        if script is None:
            story.append(Paragraph(fallback or "-", styles["Normal"]))
            story.append(Spacer(1, 8))
            return
        if script.teacher_says:
            story.append(Paragraph(f"<b>TEACHER SAYS:</b> “{script.teacher_says}”", styles["Normal"]))
        if script.do:
            story.append(Paragraph(f"<b>DO:</b> {script.do}", styles["Normal"]))
        for i, question in enumerate(script.ask):
            story.append(Paragraph(f"<b>ASK:</b> {question}", styles["Normal"]))
            if i < len(script.expected_answers):
                story.append(Paragraph(f"<b>EXPECTED ANSWER:</b> {script.expected_answers[i]}", styles["Normal"]))
        if script.students_do:
            story.append(Paragraph(f"<b>STUDENTS DO:</b> {script.students_do}", styles["Normal"]))
        if script.check_understanding:
            story.append(Paragraph(f"<b>CHECK FOR UNDERSTANDING:</b> {script.check_understanding}", styles["Normal"]))
        if script.watch_out_for:
            story.append(Paragraph(f"<b>WATCH OUT FOR:</b> {script.watch_out_for}", styles["Normal"]))
        story.append(Spacer(1, 8))

    section("Overview", content.overview)
    section("Learning objectives", content.learning_objectives)
    section("Success criteria", content.success_criteria)
    section("Key vocabulary", content.key_vocabulary)
    section("Prior knowledge", content.prior_knowledge)
    section("Resources needed", content.resources_needed)
    script_section("Starter", content.starter_script, content.starter)
    script_section("Main teaching / explanation", content.teacher_explanation_script, content.teacher_explanation)
    script_section("Guided practice", content.guided_practice_script, content.guided_practice)
    section("Independent practice", content.independent_practice)
    section("Key questions", content.key_questions)
    section("Differentiation - Support", content.differentiation.support)
    section("Differentiation - Core", content.differentiation.core)
    section("Differentiation - Greater depth", content.differentiation.greater_depth)
    section("Assessment", content.assessment)
    section("Common misconceptions", content.misconceptions)
    script_section("Plenary", content.plenary_script, content.plenary)
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


def render_worksheet_pdf(worksheet: WorksheetContent, subject_name: str, year_group_name: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    story = [Paragraph(worksheet.title, styles["Title"]), Paragraph(f"{subject_name} · {year_group_name}", styles["Normal"]), Spacer(1, 12)]

    def section(heading: str, questions: list[str]):
        story.append(Paragraph(heading, styles["Heading2"]))
        story.append(_bullets(questions) if questions else Paragraph("-", styles["Normal"]))
        story.append(Spacer(1, 8))

    story.append(Paragraph(worksheet.instructions, styles["Normal"]))
    story.append(Spacer(1, 8))
    section("Recall questions", worksheet.recall_questions)
    section("Understanding questions", worksheet.understanding_questions)
    section("Application questions", worksheet.application_questions)
    section("Challenge questions", worksheet.challenge_questions)

    doc.build(story)
    return buffer.getvalue()


def render_homework_pdf(homework: HomeworkContent, subject_name: str, year_group_name: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    story = [
        Paragraph(homework.title, styles["Title"]),
        Paragraph(f"{subject_name} · {year_group_name} · estimated {homework.estimated_minutes} minutes", styles["Normal"]),
        Spacer(1, 12),
        Paragraph(homework.instructions, styles["Normal"]),
        Spacer(1, 8),
        Paragraph("Tasks", styles["Heading2"]),
        _bullets(homework.tasks) if homework.tasks else Paragraph("-", styles["Normal"]),
    ]
    doc.build(story)
    return buffer.getvalue()
