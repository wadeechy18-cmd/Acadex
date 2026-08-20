import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.community import Discussion, QuestionThread, Report, ReportStatus
from app.models.education import Course, Lesson, Subject
from app.models.question import Question
from app.models.quiz import QuizAttempt
from app.models.user import (
    AdminProfile,
    StudentProfile,
    TeacherProfile,
    TeacherSubject,
    User,
    UserRole,
)
from app.schemas.admin import (
    AdminReportRow,
    AdminUserRow,
    PlatformStats,
    TeacherRow,
    TeacherSubjectAssign,
    TeacherVerifyUpdate,
    UserActiveUpdate,
)
from app.schemas.education import SubjectResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=PlatformStats)
def get_stats(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> PlatformStats:
    return PlatformStats(
        total_users=db.query(User).count(),
        total_students=db.query(User).filter(User.role == UserRole.STUDENT).count(),
        total_teachers=db.query(User).filter(User.role == UserRole.TEACHER).count(),
        total_admins=db.query(User).filter(User.role == UserRole.ADMIN).count(),
        total_subjects=db.query(Subject).count(),
        total_courses=db.query(Course).count(),
        total_published_courses=db.query(Course).filter(Course.is_published.is_(True)).count(),
        total_lessons=db.query(Lesson).count(),
        total_questions=db.query(Question).count(),
        total_quiz_attempts=db.query(QuizAttempt).count(),
        total_discussions=db.query(Discussion).count(),
        total_question_threads=db.query(QuestionThread).count(),
        pending_reports=db.query(Report).filter(Report.status == ReportStatus.PENDING).count(),
    )


def _display_name_for(db: Session, user: User) -> str:
    if user.role == UserRole.STUDENT:
        profile = db.query(StudentProfile).filter_by(user_id=user.id).first()
    elif user.role == UserRole.TEACHER:
        profile = db.query(TeacherProfile).filter_by(user_id=user.id).first()
    else:
        profile = db.query(AdminProfile).filter_by(user_id=user.id).first()
    return profile.display_name if profile else user.email


@router.get("/users", response_model=list[AdminUserRow])
def list_users(
    role: UserRole | None = None, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> list[AdminUserRow]:
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)

    rows = []
    for user in query.order_by(User.created_at.desc()).all():
        is_verified_teacher = None
        if user.role == UserRole.TEACHER:
            profile = db.query(TeacherProfile).filter_by(user_id=user.id).first()
            is_verified_teacher = bool(profile and profile.is_verified_teacher)
        rows.append(
            AdminUserRow(
                id=user.id,
                email=user.email,
                role=user.role,
                display_name=_display_name_for(db, user),
                is_active=user.is_active,
                is_verified=user.is_verified,
                is_verified_teacher=is_verified_teacher,
                created_at=user.created_at,
            )
        )
    return rows


@router.patch("/users/{user_id}/active", response_model=AdminUserRow)
def set_user_active(
    user_id: uuid.UUID, payload: UserActiveUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)
) -> AdminUserRow:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    if user.id == admin.id and not payload.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate your own account.")

    user.is_active = payload.is_active
    db.commit()

    is_verified_teacher = None
    if user.role == UserRole.TEACHER:
        profile = db.query(TeacherProfile).filter_by(user_id=user.id).first()
        is_verified_teacher = bool(profile and profile.is_verified_teacher)

    return AdminUserRow(
        id=user.id,
        email=user.email,
        role=user.role,
        display_name=_display_name_for(db, user),
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_verified_teacher=is_verified_teacher,
        created_at=user.created_at,
    )


@router.get("/teachers", response_model=list[TeacherRow])
def list_teachers(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[TeacherRow]:
    rows = []
    for profile in db.query(TeacherProfile).all():
        subject_ids = [row[0] for row in db.query(TeacherSubject.subject_id).filter_by(teacher_profile_id=profile.id).all()]
        subjects = db.query(Subject).filter(Subject.id.in_(subject_ids)).all() if subject_ids else []
        rows.append(
            TeacherRow(
                id=profile.id,
                user_id=profile.user_id,
                display_name=profile.display_name,
                is_verified_teacher=profile.is_verified_teacher,
                subjects=[SubjectResponse.model_validate(s) for s in subjects],
            )
        )
    return rows


@router.patch("/teachers/{teacher_profile_id}/verify", response_model=TeacherRow)
def verify_teacher(
    teacher_profile_id: uuid.UUID,
    payload: TeacherVerifyUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> TeacherRow:
    profile = db.get(TeacherProfile, teacher_profile_id)
    if not profile:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Teacher not found.")
    profile.is_verified_teacher = payload.is_verified_teacher
    db.commit()

    subject_ids = [row[0] for row in db.query(TeacherSubject.subject_id).filter_by(teacher_profile_id=profile.id).all()]
    subjects = db.query(Subject).filter(Subject.id.in_(subject_ids)).all() if subject_ids else []
    return TeacherRow(
        id=profile.id,
        user_id=profile.user_id,
        display_name=profile.display_name,
        is_verified_teacher=profile.is_verified_teacher,
        subjects=[SubjectResponse.model_validate(s) for s in subjects],
    )


@router.post("/teachers/{teacher_profile_id}/subjects", status_code=status.HTTP_201_CREATED)
def assign_teacher_subject(
    teacher_profile_id: uuid.UUID,
    payload: TeacherSubjectAssign,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    if not db.get(TeacherProfile, teacher_profile_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Teacher not found.")
    if not db.get(Subject, payload.subject_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found.")

    existing = db.query(TeacherSubject).filter_by(teacher_profile_id=teacher_profile_id, subject_id=payload.subject_id).first()
    if not existing:
        db.add(TeacherSubject(teacher_profile_id=teacher_profile_id, subject_id=payload.subject_id))
        db.commit()
    return {"status": "assigned"}


@router.delete("/teachers/{teacher_profile_id}/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_teacher_subject(
    teacher_profile_id: uuid.UUID, subject_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> None:
    row = db.query(TeacherSubject).filter_by(teacher_profile_id=teacher_profile_id, subject_id=subject_id).first()
    if row:
        db.delete(row)
        db.commit()


@router.get("/reports", response_model=list[AdminReportRow])
def list_reports(
    status_filter: ReportStatus | None = None, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> list[Report]:
    query = db.query(Report)
    if status_filter:
        query = query.filter(Report.status == status_filter)
    return query.order_by(Report.created_at.desc()).all()
