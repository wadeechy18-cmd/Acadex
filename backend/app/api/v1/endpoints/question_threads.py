import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional, require_student
from app.db.session import get_db
from app.models.community import Comment, QuestionImage, QuestionThread, QuestionThreadStatus
from app.models.education import Subject
from app.models.user import User
from app.schemas.community import (
    CommentResponse,
    QuestionImageResponse,
    QuestionThreadDetail,
    QuestionThreadResponse,
)
from app.services.community_service import build_comment_tree, save_question_images
from app.storage.base import get_storage_backend

router = APIRouter(tags=["question-threads"])


@router.post("/question-threads", response_model=QuestionThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_question_thread(
    subject_id: uuid.UUID = Form(...),
    topic_id: uuid.UUID | None = Form(None),
    description: str | None = Form(None),
    images: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    user: User = Depends(require_student),
) -> QuestionThread:
    if not db.get(Subject, subject_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found.")

    file_payloads = []
    for image in images:
        content = await image.read()
        if content:
            file_payloads.append((content, image.filename or "upload", image.content_type or "application/octet-stream"))

    storage_keys = save_question_images(file_payloads)

    thread = QuestionThread(
        student_id=user.id,
        subject_id=subject_id,
        topic_id=topic_id,
        description=description,
        status=QuestionThreadStatus.OPEN,
    )
    db.add(thread)
    db.flush()

    for key in storage_keys:
        db.add(QuestionImage(question_thread_id=thread.id, storage_key=key))

    db.commit()
    db.refresh(thread)
    return thread


@router.get("/question-threads", response_model=list[QuestionThreadResponse])
def list_question_threads(
    subject_id: uuid.UUID | None = None,
    status_filter: QuestionThreadStatus | None = None,
    db: Session = Depends(get_db),
) -> list[QuestionThread]:
    query = db.query(QuestionThread)
    if subject_id:
        query = query.filter(QuestionThread.subject_id == subject_id)
    if status_filter:
        query = query.filter(QuestionThread.status == status_filter)
    return query.order_by(QuestionThread.created_at.desc()).all()


@router.get("/question-threads/{thread_id}", response_model=QuestionThreadDetail)
def get_question_thread(
    thread_id: uuid.UUID, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)
) -> QuestionThreadDetail:
    thread = db.get(QuestionThread, thread_id)
    if not thread:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question thread not found.")

    images = db.query(QuestionImage).filter_by(question_thread_id=thread.id).all()
    storage = get_storage_backend()
    comments = db.query(Comment).filter(Comment.question_thread_id == thread.id).all()

    return QuestionThreadDetail(
        id=thread.id,
        student_id=thread.student_id,
        subject_id=thread.subject_id,
        topic_id=thread.topic_id,
        description=thread.description,
        status=thread.status,
        created_at=thread.created_at,
        images=[QuestionImageResponse(id=img.id, url=storage.url_for(img.storage_key)) for img in images],
        comments=build_comment_tree(db, comments, user.id if user else None),
    )


@router.get("/question-threads/{thread_id}/comments", response_model=list[CommentResponse])
def get_question_thread_comments(
    thread_id: uuid.UUID, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)
) -> list[CommentResponse]:
    if not db.get(QuestionThread, thread_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question thread not found.")
    comments = db.query(Comment).filter(Comment.question_thread_id == thread_id).all()
    return build_comment_tree(db, comments, user.id if user else None)
