import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.community import Comment, Discussion
from app.models.education import Topic
from app.models.user import User
from app.schemas.community import CommentResponse, DiscussionCreate, DiscussionResponse
from app.services.community_service import build_comment_tree

router = APIRouter(tags=["discussions"])


@router.get("/topics/{topic_id}/discussions", response_model=list[DiscussionResponse])
def list_topic_discussions(topic_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Discussion]:
    return db.query(Discussion).filter(Discussion.topic_id == topic_id).order_by(Discussion.created_at.desc()).all()


@router.post("/discussions", response_model=DiscussionResponse, status_code=status.HTTP_201_CREATED)
def create_discussion(payload: DiscussionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Discussion:
    if not db.get(Topic, payload.topic_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic not found.")
    discussion = Discussion(topic_id=payload.topic_id, title=payload.title, created_by_id=user.id)
    db.add(discussion)
    db.commit()
    db.refresh(discussion)
    return discussion


@router.get("/discussions/{discussion_id}/comments", response_model=list[CommentResponse])
def get_discussion_comments(
    discussion_id: uuid.UUID, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)
) -> list[CommentResponse]:
    if not db.get(Discussion, discussion_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Discussion not found.")
    comments = db.query(Comment).filter(Comment.discussion_id == discussion_id).all()
    return build_comment_tree(db, comments, user.id if user else None)
