import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.curriculum import (
    CurriculumResponse,
    CurriculumTopicResponse,
    KeyStageResponse,
    ObjectiveResponse,
    SubjectResponse,
    YearGroupResponse,
)
from app.services import curriculum_service

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


@router.get("/curricula", response_model=list[CurriculumResponse])
def list_curricula(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[CurriculumResponse]:
    return curriculum_service.list_curricula(db)


@router.get("/curricula/{curriculum_id}/key-stages", response_model=list[KeyStageResponse])
def list_key_stages(curriculum_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[KeyStageResponse]:
    return curriculum_service.list_key_stages(db, curriculum_id)


@router.get("/key-stages/{key_stage_id}/year-groups", response_model=list[YearGroupResponse])
def list_year_groups(key_stage_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[YearGroupResponse]:
    return curriculum_service.list_year_groups(db, key_stage_id)


@router.get("/year-groups/{year_group_id}/subjects", response_model=list[SubjectResponse])
def list_subjects(year_group_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[SubjectResponse]:
    return curriculum_service.list_subjects_for_year_group(db, year_group_id)


@router.get("/topics", response_model=list[CurriculumTopicResponse])
def list_topics(
    subject_id: uuid.UUID, year_group_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[CurriculumTopicResponse]:
    return curriculum_service.list_topics(db, subject_id, year_group_id)


@router.get("/topics/{topic_id}/objectives", response_model=list[ObjectiveResponse])
def list_objectives(topic_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[ObjectiveResponse]:
    return curriculum_service.list_objectives(db, topic_id)
