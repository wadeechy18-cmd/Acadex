import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.education import Chapter, Course, Lesson, Subject, Topic
from app.models.user import TeacherSubject, User, UserRole


def slug_conflict(db: Session, model, slug: str, exclude_id: uuid.UUID | None = None) -> bool:
    query = db.query(model).filter(model.slug == slug)
    if exclude_id:
        query = query.filter(model.id != exclude_id)
    return db.query(query.exists()).scalar()


def require_unique_slug(db: Session, model, slug: str, exclude_id: uuid.UUID | None = None) -> None:
    if slug_conflict(db, model, slug, exclude_id):
        raise HTTPException(status.HTTP_409_CONFLICT, f"The slug '{slug}' is already in use.")


def get_or_404(db: Session, model, id_: uuid.UUID, name: str):
    obj = db.get(model, id_)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{name} not found.")
    return obj


def teacher_subject_ids(db: Session, teacher_id: uuid.UUID) -> set[uuid.UUID]:
    from app.models.user import TeacherProfile

    profile = db.query(TeacherProfile).filter_by(user_id=teacher_id).first()
    if not profile:
        return set()
    rows = db.query(TeacherSubject.subject_id).filter(TeacherSubject.teacher_profile_id == profile.id).all()
    return {row[0] for row in rows}


def assert_can_manage_subject(db: Session, user: User, subject_id: uuid.UUID) -> None:
    if user.role == UserRole.ADMIN:
        return
    if user.role == UserRole.TEACHER and subject_id in teacher_subject_ids(db, user.id):
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized to manage content for this subject.")


def assert_can_manage_course(db: Session, user: User, course_id: uuid.UUID) -> Course:
    course = get_or_404(db, Course, course_id, "Course")
    assert_can_manage_subject(db, user, course.subject_id)
    return course


def assert_can_manage_chapter(db: Session, user: User, chapter_id: uuid.UUID) -> Chapter:
    chapter = get_or_404(db, Chapter, chapter_id, "Chapter")
    assert_can_manage_course(db, user, chapter.course_id)
    return chapter


def assert_can_manage_topic(db: Session, user: User, topic_id: uuid.UUID) -> Topic:
    topic = db.query(Topic).options(joinedload(Topic.chapter)).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic not found.")
    assert_can_manage_course(db, user, topic.chapter.course_id)
    return topic


def assert_can_manage_lesson(db: Session, user: User, lesson_id: uuid.UUID) -> Lesson:
    lesson = db.query(Lesson).options(joinedload(Lesson.topic)).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found.")
    assert_can_manage_course(db, user, lesson.topic.chapter.course_id)
    return lesson


def get_breadcrumb(db: Session, topic: Topic) -> tuple[Chapter, Course, Subject]:
    chapter = db.get(Chapter, topic.chapter_id)
    course = db.get(Course, chapter.course_id)
    subject = db.get(Subject, course.subject_id)
    return chapter, course, subject


def visible_course_filter(user: User | None):
    """Unpublished courses are only visible to admins and teachers (who need to
    preview their own draft content before publishing).
    """
    if user and user.role in (UserRole.ADMIN, UserRole.TEACHER):
        return None
    return Course.is_published.is_(True)
