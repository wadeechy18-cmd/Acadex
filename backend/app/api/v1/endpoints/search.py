from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.education import Course, Lesson, Subject, Topic
from app.models.pastpaper import PastPaper
from app.schemas.search import SearchResponse, SearchResult

router = APIRouter(tags=["search"])

RESULTS_PER_TYPE = 5


@router.get("/search", response_model=SearchResponse)
def search(q: str = Query(min_length=1, max_length=200), db: Session = Depends(get_db)) -> SearchResponse:
    pattern = f"%{q}%"
    results: list[SearchResult] = []

    for subject in db.query(Subject).filter(Subject.name.ilike(pattern)).limit(RESULTS_PER_TYPE).all():
        results.append(SearchResult(type="subject", id=subject.id, title=subject.name, subtitle="Subject", url=f"/subjects/{subject.slug}"))

    for course in (
        db.query(Course).filter(Course.title.ilike(pattern), Course.is_published.is_(True)).limit(RESULTS_PER_TYPE).all()
    ):
        results.append(SearchResult(type="course", id=course.id, title=course.title, subtitle="Course", url=f"/courses/{course.slug}"))

    for lesson in (
        db.query(Lesson)
        .join(Topic, Lesson.topic_id == Topic.id)
        .filter(Lesson.title.ilike(pattern), Lesson.is_published.is_(True))
        .limit(RESULTS_PER_TYPE)
        .all()
    ):
        results.append(SearchResult(type="lesson", id=lesson.id, title=lesson.title, subtitle="Lesson", url=f"/lessons/{lesson.slug}"))

    for paper in db.query(PastPaper).filter(PastPaper.title.ilike(pattern)).limit(RESULTS_PER_TYPE).all():
        results.append(SearchResult(type="past_paper", id=paper.id, title=paper.title, subtitle="Past paper", url=f"/past-papers/{paper.id}"))

    return SearchResponse(results=results)
