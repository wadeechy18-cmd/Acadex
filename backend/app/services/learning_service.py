import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.education import Chapter, Course, Topic
from app.models.learning import Bookmark, Enrollment, EnrollmentStatus, Progress


def topic_ids_for_course(db: Session, course_id: uuid.UUID) -> list[uuid.UUID]:
    rows = db.query(Topic.id).join(Chapter, Topic.chapter_id == Chapter.id).filter(Chapter.course_id == course_id).all()
    return [row[0] for row in rows]


def course_completion_percentage(db: Session, student_id: uuid.UUID, course_id: uuid.UUID) -> float:
    topic_ids = topic_ids_for_course(db, course_id)
    if not topic_ids:
        return 0.0

    progress_rows = (
        db.query(Progress.completion_percentage)
        .filter(Progress.student_id == student_id, Progress.topic_id.in_(topic_ids))
        .all()
    )
    total = sum(row[0] for row in progress_rows)
    return round(total / len(topic_ids), 1)


def enroll_student(db: Session, student_id: uuid.UUID, course_id: uuid.UUID) -> Enrollment:
    course = db.get(Course, course_id)
    if not course or not course.is_published:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found.")

    existing = db.query(Enrollment).filter_by(student_id=student_id, course_id=course_id).first()
    if existing:
        if existing.status != EnrollmentStatus.ACTIVE:
            existing.status = EnrollmentStatus.ACTIVE
            db.commit()
            db.refresh(existing)
        return existing

    enrollment = Enrollment(student_id=student_id, course_id=course_id, status=EnrollmentStatus.ACTIVE)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def unenroll_student(db: Session, student_id: uuid.UUID, course_id: uuid.UUID) -> None:
    enrollment = db.query(Enrollment).filter_by(student_id=student_id, course_id=course_id).first()
    if not enrollment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Enrollment not found.")
    enrollment.status = EnrollmentStatus.DROPPED
    db.commit()


def upsert_progress(
    db: Session, student_id: uuid.UUID, topic_id: uuid.UUID, completion_percentage: float, last_position_seconds: int | None
) -> Progress:
    if not db.get(Topic, topic_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic not found.")

    progress = db.query(Progress).filter_by(student_id=student_id, topic_id=topic_id).first()
    if not progress:
        progress = Progress(student_id=student_id, topic_id=topic_id, completion_percentage=0.0)
        db.add(progress)

    progress.completion_percentage = completion_percentage
    if last_position_seconds is not None:
        progress.last_position_seconds = last_position_seconds
    if completion_percentage >= 100 and progress.completed_at is None:
        progress.completed_at = datetime.now(timezone.utc)
    elif completion_percentage < 100:
        progress.completed_at = None

    db.commit()
    db.refresh(progress)
    return progress


def toggle_bookmark(db: Session, student_id: uuid.UUID, target_type, target_id: uuid.UUID) -> Bookmark:
    existing = db.query(Bookmark).filter_by(student_id=student_id, target_type=target_type, target_id=target_id).first()
    if existing:
        return existing
    bookmark = Bookmark(student_id=student_id, target_type=target_type, target_id=target_id)
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return bookmark


def remove_bookmark(db: Session, student_id: uuid.UUID, bookmark_id: uuid.UUID) -> None:
    bookmark = db.query(Bookmark).filter_by(id=bookmark_id, student_id=student_id).first()
    if not bookmark:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bookmark not found.")
    db.delete(bookmark)
    db.commit()
