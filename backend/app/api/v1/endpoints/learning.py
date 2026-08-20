import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.db.session import get_db
from app.models.education import Course, Topic
from app.models.learning import Bookmark, Enrollment, EnrollmentStatus, Progress
from app.models.user import User
from app.schemas.education import CourseResponse, TopicResponse
from app.schemas.learning import (
    BookmarkCreate,
    BookmarkResponse,
    DashboardSummary,
    EnrollmentCreate,
    EnrollmentResponse,
    EnrollmentWithCourse,
    ProgressResponse,
    ProgressUpdate,
    ProgressWithTopic,
)
from app.services.learning_service import (
    course_completion_percentage,
    enroll_student,
    remove_bookmark,
    toggle_bookmark,
    unenroll_student,
    upsert_progress,
)

router = APIRouter(tags=["learning"])


def _enrollment_with_course(db: Session, student_id: uuid.UUID, enrollment: Enrollment) -> EnrollmentWithCourse | None:
    course = db.get(Course, enrollment.course_id)
    if not course:
        return None
    return EnrollmentWithCourse(
        id=enrollment.id,
        course_id=enrollment.course_id,
        status=enrollment.status,
        enrolled_at=enrollment.enrolled_at,
        course=CourseResponse.model_validate(course),
        completion_percentage=course_completion_percentage(db, student_id, enrollment.course_id),
    )


def _progress_with_topic(db: Session, progress: Progress) -> ProgressWithTopic | None:
    topic = db.get(Topic, progress.topic_id)
    if not topic:
        return None
    return ProgressWithTopic(
        id=progress.id,
        topic_id=progress.topic_id,
        completion_percentage=progress.completion_percentage,
        last_position_seconds=progress.last_position_seconds,
        completed_at=progress.completed_at,
        topic=TopicResponse.model_validate(topic),
    )


@router.post("/enrollments", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
def create_enrollment(
    payload: EnrollmentCreate, db: Session = Depends(get_db), user: User = Depends(require_student)
) -> Enrollment:
    return enroll_student(db, user.id, payload.course_id)


@router.get("/enrollments/me", response_model=list[EnrollmentWithCourse])
def list_my_enrollments(
    db: Session = Depends(get_db), user: User = Depends(require_student)
) -> list[EnrollmentWithCourse]:
    enrollments = (
        db.query(Enrollment).filter(Enrollment.student_id == user.id, Enrollment.status == EnrollmentStatus.ACTIVE).all()
    )
    results = [_enrollment_with_course(db, user.id, e) for e in enrollments]
    return [r for r in results if r is not None]


@router.delete("/enrollments/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_enrollment(course_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_student)) -> None:
    unenroll_student(db, user.id, course_id)


@router.put("/progress/{topic_id}", response_model=ProgressResponse)
def update_progress(
    topic_id: uuid.UUID,
    payload: ProgressUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_student),
) -> Progress:
    return upsert_progress(db, user.id, topic_id, payload.completion_percentage, payload.last_position_seconds)


@router.get("/progress/me", response_model=list[ProgressWithTopic])
def list_my_progress(db: Session = Depends(get_db), user: User = Depends(require_student)) -> list[ProgressWithTopic]:
    rows = db.query(Progress).filter(Progress.student_id == user.id).all()
    results = [_progress_with_topic(db, p) for p in rows]
    return [r for r in results if r is not None]


@router.post("/bookmarks", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED)
def create_bookmark(payload: BookmarkCreate, db: Session = Depends(get_db), user: User = Depends(require_student)) -> Bookmark:
    return toggle_bookmark(db, user.id, payload.target_type, payload.target_id)


@router.get("/bookmarks/me", response_model=list[BookmarkResponse])
def list_my_bookmarks(db: Session = Depends(get_db), user: User = Depends(require_student)) -> list[Bookmark]:
    return db.query(Bookmark).filter(Bookmark.student_id == user.id).order_by(Bookmark.created_at.desc()).all()


@router.delete("/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(bookmark_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_student)) -> None:
    remove_bookmark(db, user.id, bookmark_id)


@router.get("/dashboard/me", response_model=DashboardSummary)
def get_dashboard(db: Session = Depends(get_db), user: User = Depends(require_student)) -> DashboardSummary:
    enrollments = (
        db.query(Enrollment).filter(Enrollment.student_id == user.id, Enrollment.status == EnrollmentStatus.ACTIVE).all()
    )
    my_courses = [r for r in (_enrollment_with_course(db, user.id, e) for e in enrollments) if r is not None]

    recent_rows = db.query(Progress).filter(Progress.student_id == user.id).order_by(Progress.updated_at.desc()).limit(5).all()
    recent_progress = [r for r in (_progress_with_topic(db, p) for p in recent_rows) if r is not None]

    bookmarks = db.query(Bookmark).filter(Bookmark.student_id == user.id).order_by(Bookmark.created_at.desc()).limit(10).all()

    continue_learning = next((p for p in recent_progress if p.completion_percentage < 100), None)

    return DashboardSummary(
        my_courses=my_courses,
        continue_learning=continue_learning,
        recent_progress=recent_progress,
        bookmarks=[BookmarkResponse.model_validate(b) for b in bookmarks],
    )
