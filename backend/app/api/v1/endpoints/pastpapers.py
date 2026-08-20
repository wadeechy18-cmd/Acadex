import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.education import Subject
from app.models.pastpaper import PastPaper, PastPaperQuestion, PastPaperResource, PastPaperSession
from app.models.question import Question
from app.models.user import User
from app.schemas.pastpaper import (
    PastPaperCreate,
    PastPaperDetail,
    PastPaperQuestionCreate,
    PastPaperQuestionResponse,
    PastPaperResourceCreate,
    PastPaperResourceResponse,
    PastPaperResponse,
)

router = APIRouter(tags=["past-papers"])


@router.get("/past-papers", response_model=list[PastPaperResponse])
def list_past_papers(
    subject_id: uuid.UUID | None = None,
    exam_board_id: uuid.UUID | None = None,
    year: int | None = None,
    session_filter: PastPaperSession | None = None,
    db: Session = Depends(get_db),
) -> list[PastPaper]:
    query = db.query(PastPaper)
    if subject_id:
        query = query.filter(PastPaper.subject_id == subject_id)
    if exam_board_id:
        query = query.filter(PastPaper.exam_board_id == exam_board_id)
    if year:
        query = query.filter(PastPaper.year == year)
    if session_filter:
        query = query.filter(PastPaper.session == session_filter)
    return query.order_by(PastPaper.year.desc(), PastPaper.paper_number).all()


@router.get("/past-papers/{paper_id}", response_model=PastPaperDetail)
def get_past_paper(paper_id: uuid.UUID, db: Session = Depends(get_db)) -> PastPaperDetail:
    paper = db.get(PastPaper, paper_id)
    if not paper:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Past paper not found.")

    resources = db.query(PastPaperResource).filter_by(past_paper_id=paper.id).all()
    paper_questions = db.query(PastPaperQuestion).filter_by(past_paper_id=paper.id).order_by(PastPaperQuestion.question_number).all()

    return PastPaperDetail(
        id=paper.id,
        subject_id=paper.subject_id,
        exam_board_id=paper.exam_board_id,
        title=paper.title,
        year=paper.year,
        session=paper.session,
        paper_number=paper.paper_number,
        resources=[PastPaperResourceResponse.model_validate(r) for r in resources],
        paper_questions=[PastPaperQuestionResponse.model_validate(q) for q in paper_questions],
    )


@router.post("/past-papers", response_model=PastPaperResponse, status_code=status.HTTP_201_CREATED)
def create_past_paper(payload: PastPaperCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> PastPaper:
    if not db.get(Subject, payload.subject_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found.")

    existing = db.query(PastPaper).filter_by(
        subject_id=payload.subject_id, year=payload.year, session=payload.session, paper_number=payload.paper_number
    ).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "A past paper with this subject/year/session/paper number already exists.")

    paper = PastPaper(**payload.model_dump())
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return paper


@router.post(
    "/past-papers/{paper_id}/resources", response_model=PastPaperResourceResponse, status_code=status.HTTP_201_CREATED
)
def add_past_paper_resource(
    paper_id: uuid.UUID, payload: PastPaperResourceCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> PastPaperResource:
    if not db.get(PastPaper, paper_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Past paper not found.")

    resource = PastPaperResource(past_paper_id=paper_id, **payload.model_dump())
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


@router.post(
    "/past-papers/{paper_id}/questions", response_model=PastPaperQuestionResponse, status_code=status.HTTP_201_CREATED
)
def link_past_paper_question(
    paper_id: uuid.UUID, payload: PastPaperQuestionCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> PastPaperQuestion:
    if not db.get(PastPaper, paper_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Past paper not found.")
    if not db.get(Question, payload.question_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found.")

    link = PastPaperQuestion(past_paper_id=paper_id, **payload.model_dump())
    db.add(link)
    db.commit()
    db.refresh(link)
    return link
