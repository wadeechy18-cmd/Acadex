import re
import uuid
from typing import Literal

from sqlalchemy.orm import Session

from app.export import docx as docx_export
from app.export import pdf as pdf_export
from app.models.user import User
from app.models.worksheet import Homework, Worksheet
from app.schemas.lesson_plan import LessonPlanContent
from app.schemas.worksheet import PracticeSetContent
from app.services import lesson_plan_service, practice_set_service

ExportFormat = Literal["pdf", "docx"]

_DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_MEDIA_TYPES: dict[ExportFormat, str] = {"pdf": "application/pdf", "docx": _DOCX_MEDIA_TYPE}


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 _-]", "", name).strip().replace(" ", "_")
    return cleaned or "export"


def export_lesson_plan(
    db: Session, user: User, lesson_plan_id: uuid.UUID, fmt: ExportFormat
) -> tuple[bytes, str, str]:
    lesson_plan = lesson_plan_service.get_lesson_plan(db, user, lesson_plan_id)  # view access, same as reading it
    latest = lesson_plan_service.get_latest_version(db, lesson_plan.id)
    content = LessonPlanContent.model_validate(latest.content)

    kwargs = dict(title=lesson_plan.title, topic=lesson_plan.topic, duration_minutes=lesson_plan.duration_minutes, content=content)
    data = pdf_export.render_lesson_plan_pdf(**kwargs) if fmt == "pdf" else docx_export.render_lesson_plan_docx(**kwargs)
    filename = f"{_safe_filename(lesson_plan.title)}.{fmt}"
    return data, filename, _MEDIA_TYPES[fmt]


def export_practice_set(
    db: Session, user: User, model_cls: type[Worksheet] | type[Homework], item_id: uuid.UUID, fmt: ExportFormat, include_answers: bool
) -> tuple[bytes, str, str]:
    item = practice_set_service.get_one(db, user, model_cls, item_id)  # view access, same as reading it
    content = PracticeSetContent.model_validate(item.content)
    due_date = item.due_date.isoformat() if isinstance(item, Homework) and item.due_date else None

    kwargs = dict(title=item.title, due_date=due_date, content=content, include_answers=include_answers)
    data = pdf_export.render_practice_set_pdf(**kwargs) if fmt == "pdf" else docx_export.render_practice_set_docx(**kwargs)
    suffix = "answers" if include_answers else "student"
    filename = f"{_safe_filename(item.title)}_{suffix}.{fmt}"
    return data, filename, _MEDIA_TYPES[fmt]
