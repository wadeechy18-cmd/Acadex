from app.models.user import SchoolAdminProfile, TeacherProfile, User, UserRole
from app.models.school import School, SchoolMembership, SchoolMembershipRole
from app.models.curriculum import (
    Curriculum,
    CurriculumTopic,
    KeyStage,
    Objective,
    ProgrammeOfStudy,
    Subject,
    YearGroup,
)
from app.models.resource import ExtractionStatus, Resource, ResourceKind
from app.models.lesson_plan import AbilityLevel, GenerationKind, LessonPlan, LessonPlanVersion, LessonPlanVersionResource
from app.models.class_ import Class
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.timetable import (
    AcademicYear,
    AvailabilityStatus,
    ClassSubjectRequirement,
    Room,
    TeacherAvailability,
    TeacherSubjectQualification,
    TimeSlot,
    Timetable,
    TimetableEntry,
)
from app.models.absence import AffectedLesson, TeacherAbsence
from app.models.substitution import (
    AssignmentStatus,
    Notification,
    SubstitutionAssignment,
    SubstitutionPlan,
    SubstitutionPlanStatus,
    TimetableException,
)
from app.models.audit_log import AuditLog

__all__ = [
    "User",
    "UserRole",
    "TeacherProfile",
    "SchoolAdminProfile",
    "School",
    "SchoolMembership",
    "SchoolMembershipRole",
    "Curriculum",
    "KeyStage",
    "YearGroup",
    "Subject",
    "ProgrammeOfStudy",
    "CurriculumTopic",
    "Objective",
    "Resource",
    "ResourceKind",
    "ExtractionStatus",
    "LessonPlan",
    "LessonPlanVersion",
    "LessonPlanVersionResource",
    "AbilityLevel",
    "GenerationKind",
    "Class",
    "Task",
    "TaskPriority",
    "TaskStatus",
    "AcademicYear",
    "Room",
    "TimeSlot",
    "Timetable",
    "TimetableEntry",
    "TeacherSubjectQualification",
    "TeacherAvailability",
    "AvailabilityStatus",
    "ClassSubjectRequirement",
    "TeacherAbsence",
    "AffectedLesson",
    "SubstitutionPlan",
    "SubstitutionPlanStatus",
    "SubstitutionAssignment",
    "AssignmentStatus",
    "TimetableException",
    "Notification",
    "AuditLog",
]
