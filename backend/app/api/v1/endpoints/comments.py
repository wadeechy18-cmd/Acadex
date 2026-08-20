import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.community import Report, ReportStatus
from app.models.user import User, UserRole
from app.schemas.community import (
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    ReportCreate,
    VoteRequest,
)
from app.services.community_service import (
    assert_can_edit_comment,
    assert_can_moderate,
    cast_vote,
    create_comment,
    create_report,
    get_author,
    my_vote,
    vote_score,
)

router = APIRouter(tags=["comments"])


def _to_response(db: Session, comment, viewer_id: uuid.UUID | None) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        body="[deleted]" if comment.is_deleted else comment.body,
        is_verified_teacher_answer=comment.is_verified_teacher_answer,
        is_pinned=comment.is_pinned,
        is_deleted=comment.is_deleted,
        created_at=comment.created_at,
        author=get_author(db, comment.author_id),
        vote_score=vote_score(db, comment.id),
        my_vote=my_vote(db, viewer_id, comment.id),
        replies=[],
    )


@router.post("/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def post_comment(payload: CommentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> CommentResponse:
    comment = create_comment(
        db, user, payload.discussion_id, payload.question_thread_id, payload.parent_comment_id, payload.body
    )
    return _to_response(db, comment, user.id)


@router.put("/comments/{comment_id}", response_model=CommentResponse)
def edit_comment(
    comment_id: uuid.UUID, payload: CommentUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> CommentResponse:
    comment = assert_can_edit_comment(db, user, comment_id)
    comment.body = payload.body
    db.commit()
    db.refresh(comment)
    return _to_response(db, comment, user.id)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    comment = assert_can_edit_comment(db, user, comment_id)
    comment.is_deleted = True
    db.commit()


@router.post("/comments/{comment_id}/vote", response_model=dict)
def vote_on_comment(
    comment_id: uuid.UUID, payload: VoteRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    score = cast_vote(db, user.id, comment_id, payload.value)
    return {"vote_score": score}


@router.post("/comments/{comment_id}/pin", response_model=CommentResponse)
def pin_comment(comment_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> CommentResponse:
    from app.models.community import Comment

    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comment not found.")
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only teachers and admins can pin comments.")
    assert_can_moderate(db, user, comment)

    comment.is_pinned = not comment.is_pinned
    db.commit()
    db.refresh(comment)
    return _to_response(db, comment, user.id)


@router.post("/comments/{comment_id}/verify", response_model=CommentResponse)
def mark_verified_answer(comment_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> CommentResponse:
    from app.models.community import Comment

    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comment not found.")
    if user.role != UserRole.TEACHER or comment.author_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the teacher who wrote this answer can mark it verified.")
    assert_can_moderate(db, user, comment)

    comment.is_verified_teacher_answer = not comment.is_verified_teacher_answer
    db.commit()
    db.refresh(comment)
    return _to_response(db, comment, user.id)


@router.post("/reports", status_code=status.HTTP_201_CREATED)
def report_content(payload: ReportCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    report = create_report(db, user, payload.target_type, payload.target_id, payload.reason)
    return {"id": str(report.id), "status": report.status.value}


@router.put("/reports/{report_id}/resolve", status_code=status.HTTP_200_OK)
def resolve_report(report_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_admin)) -> dict:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found.")
    report.status = ReportStatus.RESOLVED
    report.resolved_by_id = user.id
    db.commit()
    return {"id": str(report.id), "status": report.status.value}
