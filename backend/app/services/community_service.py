import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.community import (
    Comment,
    Discussion,
    QuestionThread,
    Report,
    ReportStatus,
    Vote,
    VoteTargetType,
)
from app.models.user import AdminProfile, StudentProfile, TeacherProfile, User, UserRole
from app.schemas.community import CommentAuthor, CommentResponse
from app.storage.base import (
    ALLOWED_IMAGE_TYPES,
    MAX_IMAGE_SIZE_BYTES,
    get_storage_backend,
)


def get_author(db: Session, user_id: uuid.UUID) -> CommentAuthor:
    user = db.get(User, user_id)
    if not user:
        return CommentAuthor(id=user_id, display_name="Deleted user", role=UserRole.STUDENT)

    if user.role == UserRole.STUDENT:
        profile = db.query(StudentProfile).filter_by(user_id=user.id).first()
        return CommentAuthor(id=user.id, display_name=profile.display_name if profile else user.email, role=user.role)
    if user.role == UserRole.TEACHER:
        profile = db.query(TeacherProfile).filter_by(user_id=user.id).first()
        return CommentAuthor(
            id=user.id,
            display_name=profile.display_name if profile else user.email,
            role=user.role,
            is_verified_teacher=bool(profile and profile.is_verified_teacher),
        )
    profile = db.query(AdminProfile).filter_by(user_id=user.id).first()
    return CommentAuthor(id=user.id, display_name=profile.display_name if profile else user.email, role=user.role)


def vote_score(db: Session, comment_id: uuid.UUID) -> int:
    votes = db.query(Vote.value).filter_by(target_type=VoteTargetType.COMMENT, target_id=comment_id).all()
    return sum(v[0] for v in votes)


def my_vote(db: Session, user_id: uuid.UUID | None, comment_id: uuid.UUID) -> int | None:
    if not user_id:
        return None
    vote = db.query(Vote).filter_by(user_id=user_id, target_type=VoteTargetType.COMMENT, target_id=comment_id).first()
    return vote.value if vote else None


def build_comment_tree(db: Session, comments: list[Comment], viewer_id: uuid.UUID | None) -> list[CommentResponse]:
    by_parent: dict[uuid.UUID | None, list[Comment]] = {}
    for c in comments:
        by_parent.setdefault(c.parent_comment_id, []).append(c)

    def build(parent_id: uuid.UUID | None) -> list[CommentResponse]:
        nodes = []
        for c in sorted(by_parent.get(parent_id, []), key=lambda x: x.created_at):
            nodes.append(
                CommentResponse(
                    id=c.id,
                    body="[deleted]" if c.is_deleted else c.body,
                    is_verified_teacher_answer=c.is_verified_teacher_answer,
                    is_pinned=c.is_pinned,
                    is_deleted=c.is_deleted,
                    created_at=c.created_at,
                    author=get_author(db, c.author_id),
                    vote_score=vote_score(db, c.id),
                    my_vote=my_vote(db, viewer_id, c.id),
                    replies=build(c.id),
                )
            )
        return nodes

    return build(None)


def create_comment(
    db: Session,
    user: User,
    discussion_id: uuid.UUID | None,
    question_thread_id: uuid.UUID | None,
    parent_comment_id: uuid.UUID | None,
    body: str,
) -> Comment:
    from app.services.notification_service import notify_comment_reply, notify_teacher_answer

    if not discussion_id and not question_thread_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "A comment must belong to a discussion or a question thread.")
    if discussion_id and not db.get(Discussion, discussion_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Discussion not found.")
    question_thread = db.get(QuestionThread, question_thread_id) if question_thread_id else None
    if question_thread_id and not question_thread:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question thread not found.")
    parent_comment = db.get(Comment, parent_comment_id) if parent_comment_id else None
    if parent_comment_id and not parent_comment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Parent comment not found.")

    comment = Comment(
        discussion_id=discussion_id,
        question_thread_id=question_thread_id,
        parent_comment_id=parent_comment_id,
        author_id=user.id,
        body=body,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    if parent_comment and parent_comment.author_id != user.id:
        notify_comment_reply(db, parent_comment.author_id, comment.id, discussion_id, question_thread_id)
    elif question_thread and question_thread.student_id != user.id:
        if user.role == UserRole.TEACHER:
            notify_teacher_answer(db, question_thread.student_id, comment.id, question_thread.id)
        else:
            notify_comment_reply(db, question_thread.student_id, comment.id, discussion_id, question_thread_id)

    return comment


def assert_can_edit_comment(db: Session, user: User, comment_id: uuid.UUID) -> Comment:
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comment not found.")
    if comment.author_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only edit your own comments.")
    return comment


def cast_vote(db: Session, user_id: uuid.UUID, comment_id: uuid.UUID, value: int) -> int:
    if not db.get(Comment, comment_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comment not found.")

    existing = db.query(Vote).filter_by(user_id=user_id, target_type=VoteTargetType.COMMENT, target_id=comment_id).first()
    if value == 0 or (existing and existing.value == value):
        if existing:
            db.delete(existing)
    elif existing:
        existing.value = value
    else:
        db.add(Vote(user_id=user_id, target_type=VoteTargetType.COMMENT, target_id=comment_id, value=value))

    db.commit()
    return vote_score(db, comment_id)


def create_report(db: Session, user: User, target_type, target_id: uuid.UUID, reason: str) -> Report:
    report = Report(reported_by_id=user.id, target_type=target_type, target_id=target_id, reason=reason, status=ReportStatus.PENDING)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def assert_can_moderate(db: Session, user: User, comment: Comment) -> None:
    """Teachers may pin/verify comments only within discussions on topics under a
    subject they're assigned to, or question threads for such a subject. Admins
    can moderate anything.
    """
    from app.services.education_service import assert_can_manage_subject

    if user.role == UserRole.ADMIN:
        return

    if comment.discussion_id:
        discussion = db.get(Discussion, comment.discussion_id)
        from app.services.education_service import get_breadcrumb
        from app.models.education import Topic

        topic = db.get(Topic, discussion.topic_id) if discussion else None
        if not topic:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to moderate this comment.")
        _, course, _ = get_breadcrumb(db, topic)
        assert_can_manage_subject(db, user, course.subject_id)
        return

    if comment.question_thread_id:
        thread = db.get(QuestionThread, comment.question_thread_id)
        if not thread:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to moderate this comment.")
        assert_can_manage_subject(db, user, thread.subject_id)
        return

    raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to moderate this comment.")


def save_question_images(files: list[tuple[bytes, str, str]]) -> list[str]:
    """files: list of (content_bytes, filename, content_type). Returns storage keys."""
    backend = get_storage_backend()
    keys = []
    for content, filename, content_type in files:
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported image type: {content_type}")
        if len(content) > MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Image exceeds the 10MB size limit.")
        keys.append(backend.save(content, filename, content_type, folder="question-images"))
    return keys
