import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.community import ReportStatus, ReportTargetType
from app.models.user import UserRole
from app.schemas.education import SubjectResponse


class PlatformStats(BaseModel):
    total_users: int
    total_students: int
    total_teachers: int
    total_admins: int
    total_subjects: int
    total_courses: int
    total_published_courses: int
    total_lessons: int
    total_questions: int
    total_quiz_attempts: int
    total_discussions: int
    total_question_threads: int
    pending_reports: int


class AdminUserRow(BaseModel):
    id: uuid.UUID
    email: str
    role: UserRole
    display_name: str
    is_active: bool
    is_verified: bool
    is_verified_teacher: bool | None = None
    created_at: datetime


class UserActiveUpdate(BaseModel):
    is_active: bool


class TeacherVerifyUpdate(BaseModel):
    is_verified_teacher: bool


class TeacherSubjectAssign(BaseModel):
    subject_id: uuid.UUID


class TeacherRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    is_verified_teacher: bool
    subjects: list[SubjectResponse]


class AdminReportRow(BaseModel):
    id: uuid.UUID
    reported_by_id: uuid.UUID
    target_type: ReportTargetType
    target_id: uuid.UUID
    reason: str
    status: ReportStatus
    created_at: datetime
