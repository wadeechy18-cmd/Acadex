import uuid
from datetime import date, time

from pydantic import BaseModel, Field

from app.models.timetable import AvailabilityStatus


class AcademicYearCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date


class AcademicYearResponse(BaseModel):
    id: uuid.UUID
    name: str
    start_date: date
    end_date: date


class RoomCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    capacity: int | None = None


class RoomResponse(BaseModel):
    id: uuid.UUID
    name: str
    capacity: int | None


class TimeSlotCreateRequest(BaseModel):
    day_of_week: int = Field(ge=0, le=4)
    start_time: time
    end_time: time
    label: str = Field(min_length=1, max_length=100)


class TimeSlotResponse(BaseModel):
    id: uuid.UUID
    day_of_week: int
    start_time: time
    end_time: time
    label: str


class TimetableCreateRequest(BaseModel):
    academic_year_id: uuid.UUID
    name: str = Field(min_length=1, max_length=150)


class TimetableResponse(BaseModel):
    id: uuid.UUID
    academic_year_id: uuid.UUID
    name: str


class TimetableEntryUpsertRequest(BaseModel):
    time_slot_id: uuid.UUID
    teacher_user_id: uuid.UUID
    subject_id: uuid.UUID
    class_id: uuid.UUID | None = None
    room_id: uuid.UUID | None = None


class TimetableEntryResponse(BaseModel):
    id: uuid.UUID
    time_slot_id: uuid.UUID
    teacher_user_id: uuid.UUID
    teacher_name: str
    subject_id: uuid.UUID
    subject_name: str
    class_id: uuid.UUID | None
    class_name: str | None
    room_id: uuid.UUID | None
    room_name: str | None


class QualificationCreateRequest(BaseModel):
    subject_id: uuid.UUID


class QualificationResponse(BaseModel):
    id: uuid.UUID
    subject_id: uuid.UUID
    subject_name: str


class ClassSubjectRequirementCreateRequest(BaseModel):
    class_id: uuid.UUID
    subject_id: uuid.UUID
    periods_per_week: int = Field(ge=1, le=20)


class ClassSubjectRequirementResponse(BaseModel):
    id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    subject_id: uuid.UUID
    subject_name: str
    periods_per_week: int


class RequirementScheduleSummary(BaseModel):
    requirement_id: uuid.UUID
    class_name: str
    subject_name: str
    requested_periods: int
    scheduled_periods: int


class GenerateTimetableResult(BaseModel):
    entries: list[TimetableEntryResponse]
    requirements_summary: list[RequirementScheduleSummary]


class AvailabilitySetRequest(BaseModel):
    time_slot_id: uuid.UUID
    status: AvailabilityStatus


class AvailabilityResponse(BaseModel):
    time_slot_id: uuid.UUID
    status: AvailabilityStatus
