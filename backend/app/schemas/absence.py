import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class ReportAbsenceRequest(BaseModel):
    teacher_user_id: uuid.UUID
    date: date
    reason: str | None = Field(default=None, max_length=500)


class AffectedLessonResponse(BaseModel):
    id: uuid.UUID
    timetable_entry_id: uuid.UUID
    time_slot_label: str
    day_of_week: int
    start_time: str
    end_time: str
    subject_name: str
    class_name: str | None
    room_name: str | None


class TeacherAbsenceResponse(BaseModel):
    id: uuid.UUID
    teacher_user_id: uuid.UUID
    teacher_name: str
    date: date
    reason: str | None
    reported_by_name: str
    affected_lessons: list[AffectedLessonResponse]
    created_at: datetime
