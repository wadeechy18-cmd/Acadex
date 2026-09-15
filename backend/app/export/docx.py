import io

import docx

from app.schemas.lesson_plan_content import HomeworkContent, LessonPlanContent, WorksheetContent


def render_lesson_plan_docx(content: LessonPlanContent, subject_name: str, year_group_name: str) -> bytes:
    document = docx.Document()
    document.add_heading(content.title, level=0)
    document.add_paragraph(f"{subject_name} · {year_group_name}")

    def section(heading: str, body):
        document.add_heading(heading, level=2)
        if isinstance(body, list):
            if body:
                for item in body:
                    document.add_paragraph(item, style="List Bullet")
            else:
                document.add_paragraph("-")
        else:
            document.add_paragraph(body or "-")

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

    document.add_heading("Timeline", level=2)
    table = document.add_table(rows=1, cols=3)
    table.style = "Light Grid Accent 1"
    header = table.rows[0].cells
    header[0].text, header[1].text, header[2].text = "Time", "Activity", "Description"
    for entry in content.timeline:
        row = table.add_row().cells
        row[0].text = f"{entry.start_minute:02d}-{entry.end_minute:02d}"
        row[1].text = entry.activity
        row[2].text = entry.description

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def render_worksheet_docx(worksheet: WorksheetContent, subject_name: str, year_group_name: str) -> bytes:
    document = docx.Document()
    document.add_heading(worksheet.title, level=0)
    document.add_paragraph(f"{subject_name} · {year_group_name}")
    document.add_paragraph(worksheet.instructions)

    def section(heading: str, questions: list[str]):
        document.add_heading(heading, level=2)
        if questions:
            for q in questions:
                document.add_paragraph(q, style="List Number")
        else:
            document.add_paragraph("-")

    section("Recall questions", worksheet.recall_questions)
    section("Understanding questions", worksheet.understanding_questions)
    section("Application questions", worksheet.application_questions)
    section("Challenge questions", worksheet.challenge_questions)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def render_homework_docx(homework: HomeworkContent, subject_name: str, year_group_name: str) -> bytes:
    document = docx.Document()
    document.add_heading(homework.title, level=0)
    document.add_paragraph(f"{subject_name} · {year_group_name} · estimated {homework.estimated_minutes} minutes")
    document.add_paragraph(homework.instructions)
    document.add_heading("Tasks", level=2)
    if homework.tasks:
        for task in homework.tasks:
            document.add_paragraph(task, style="List Number")
    else:
        document.add_paragraph("-")

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
