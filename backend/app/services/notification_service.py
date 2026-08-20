import uuid

from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType


def notify(db: Session, user_id: uuid.UUID, type_: NotificationType, title: str, payload: dict) -> None:
    db.add(Notification(user_id=user_id, type=type_, title=title, payload=payload))
    db.commit()


def notify_comment_reply(db: Session, recipient_id: uuid.UUID, comment_id: uuid.UUID, discussion_id: uuid.UUID | None, question_thread_id: uuid.UUID | None) -> None:
    notify(
        db,
        recipient_id,
        NotificationType.COMMENT_REPLY,
        "Someone replied to your comment",
        {"comment_id": str(comment_id), "discussion_id": str(discussion_id) if discussion_id else None, "question_thread_id": str(question_thread_id) if question_thread_id else None},
    )


def notify_teacher_answer(db: Session, recipient_id: uuid.UUID, comment_id: uuid.UUID, question_thread_id: uuid.UUID) -> None:
    notify(
        db,
        recipient_id,
        NotificationType.TEACHER_ANSWER,
        "A teacher answered your question",
        {"comment_id": str(comment_id), "question_thread_id": str(question_thread_id)},
    )
