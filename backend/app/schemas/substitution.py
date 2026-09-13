import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.substitution import AssignmentStatus, SubstitutionPlanStatus


class SubstitutionAssignmentResponse(BaseModel):
    id: uuid.UUID
    affected_lesson_id: uuid.UUID
    subject_name: str
    time_slot_label: str
    status: AssignmentStatus
    substitute_teacher_user_id: uuid.UUID | None
    substitute_teacher_name: str | None
    reason: str | None


class SubstitutionPlanResponse(BaseModel):
    id: uuid.UUID
    teacher_absence_id: uuid.UUID
    status: SubstitutionPlanStatus
    assignments: list[SubstitutionAssignmentResponse]
    approved_by_name: str | None
    approved_at: datetime | None
    created_at: datetime


class ReassignRequest(BaseModel):
    substitute_teacher_user_id: uuid.UUID | None


class TimetableExceptionResponse(BaseModel):
    id: uuid.UUID
    date: str
    timetable_entry_id: uuid.UUID
    subject_name: str
    time_slot_label: str
    class_name: str | None
    room_name: str | None
    original_teacher_name: str
    substitute_teacher_user_id: uuid.UUID | None
    substitute_teacher_name: str | None
    cover_lesson_plan_id: uuid.UUID | None = None
    cover_lesson_plan_title: str | None = None
    cover_lesson_plan_message: str | None = None
