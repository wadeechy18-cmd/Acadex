import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional, require_teacher_or_admin
from app.db.session import get_db
from app.models.content import Note, Video
from app.models.education import Lesson, Topic
from app.models.learning import Progress
from app.models.user import User, UserRole
from app.schemas.education import ChapterResponse, CourseResponse, SubjectResponse, TopicResponse
from app.schemas.learning import ProgressResponse
from app.schemas.lesson import (
    LessonBreadcrumb,
    LessonDetail,
    NoteCreate,
    NoteResponse,
    VideoResponse,
    VideoUpsert,
)
from app.services.education_service import assert_can_manage_lesson, get_breadcrumb
from app.services.video_service import resolve_playback_url

router = APIRouter(tags=["lessons"])


@router.get("/lessons/{slug}", response_model=LessonDetail)
def get_lesson(
    slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)
) -> LessonDetail:
    lesson = db.query(Lesson).filter(Lesson.slug == slug).first()
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found.")

    topic = db.get(Topic, lesson.topic_id)
    chapter, course, subject = get_breadcrumb(db, topic)

    is_privileged = bool(user and user.role in (UserRole.ADMIN, UserRole.TEACHER))
    if (not lesson.is_published or not course.is_published) and not is_privileged:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found.")

    video = db.query(Video).filter(Video.lesson_id == lesson.id).first()
    video_response = None
    if video:
        video_response = VideoResponse(
            id=video.id,
            provider=video.provider,
            duration_seconds=video.duration_seconds,
            playback_url=resolve_playback_url(video),
        )

    notes = db.query(Note).filter(Note.lesson_id == lesson.id).order_by(Note.order_index).all()

    my_progress = None
    if user and user.role == UserRole.STUDENT:
        progress = db.query(Progress).filter_by(student_id=user.id, topic_id=topic.id).first()
        if progress:
            my_progress = ProgressResponse.model_validate(progress)

    return LessonDetail(
        id=lesson.id,
        topic_id=lesson.topic_id,
        title=lesson.title,
        slug=lesson.slug,
        lesson_type=lesson.lesson_type,
        order_index=lesson.order_index,
        is_published=lesson.is_published,
        video=video_response,
        notes=[NoteResponse.model_validate(n) for n in notes],
        breadcrumb=LessonBreadcrumb(
            topic=TopicResponse.model_validate(topic),
            chapter=ChapterResponse.model_validate(chapter),
            course=CourseResponse.model_validate(course),
            subject=SubjectResponse.model_validate(subject),
        ),
        my_progress=my_progress,
    )


@router.put("/lessons/{lesson_id}/video", response_model=VideoResponse)
def upsert_video(
    lesson_id: uuid.UUID,
    payload: VideoUpsert,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher_or_admin),
) -> VideoResponse:
    assert_can_manage_lesson(db, user, lesson_id)

    video = db.query(Video).filter(Video.lesson_id == lesson_id).first()
    if not video:
        video = Video(lesson_id=lesson_id, provider=payload.provider)
        db.add(video)

    video.provider = payload.provider
    video.external_id = payload.external_id
    video.storage_key = payload.storage_key
    video.thumbnail_key = payload.thumbnail_key
    video.duration_seconds = payload.duration_seconds
    db.commit()
    db.refresh(video)

    return VideoResponse(
        id=video.id,
        provider=video.provider,
        duration_seconds=video.duration_seconds,
        playback_url=resolve_playback_url(video),
    )


@router.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    payload: NoteCreate, db: Session = Depends(get_db), user: User = Depends(require_teacher_or_admin)
) -> Note:
    assert_can_manage_lesson(db, user, payload.lesson_id)
    note = Note(**payload.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note
