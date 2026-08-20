import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_teacher_or_admin
from app.db.session import get_db
from app.models.education import Subject
from app.models.learning import Enrollment, EnrollmentStatus
from app.models.user import User
from app.schemas.education import SubjectResponse
from app.schemas.teacher import StudentProgressRow
from app.schemas.user import UserResponse
from app.services.auth_service import get_display_name
from app.services.education_service import assert_can_manage_course, teacher_subject_ids
from app.services.learning_service import course_completion_percentage

router = APIRouter(tags=["teacher"])


@router.get("/teachers/me/subjects", response_model=list[SubjectResponse])
def my_subjects(db: Session = Depends(get_db), user: User = Depends(require_teacher_or_admin)) -> list[Subject]:
    if user.role.value == "admin":
        return db.query(Subject).order_by(Subject.order_index).all()
    subject_ids = teacher_subject_ids(db, user.id)
    if not subject_ids:
        return []
    return db.query(Subject).filter(Subject.id.in_(subject_ids)).all()


@router.get("/courses/{course_id}/students", response_model=list[StudentProgressRow])
def course_students(
    course_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_teacher_or_admin)
) -> list[StudentProgressRow]:
    assert_can_manage_course(db, user, course_id)

    enrollments = (
        db.query(Enrollment).filter(Enrollment.course_id == course_id, Enrollment.status == EnrollmentStatus.ACTIVE).all()
    )
    rows = []
    for e in enrollments:
        student = db.get(User, e.student_id)
        if not student:
            continue
        rows.append(
            StudentProgressRow(
                student=UserResponse(
                    id=student.id,
                    email=student.email,
                    role=student.role,
                    is_active=student.is_active,
                    is_verified=student.is_verified,
                    display_name=get_display_name(db, student),
                ),
                completion_percentage=course_completion_percentage(db, student.id, course_id),
                enrolled_at=e.enrolled_at,
            )
        )
    return rows
