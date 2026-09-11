import uuid
from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.curriculum import CurriculumSubject
from app.models.user import User
from app.schemas.activity import ActivityLogResponse
from app.schemas.curriculum import CurriculumSubjectCreate, CurriculumSubjectResponse
from app.schemas.school import TeacherOverviewRow
from app.schemas.weekly_plan import WeeklyPlanDetail
from app.services import activity_service, curriculum_service, school_service, weekly_plan_service

router = APIRouter(tags=["school"])


@router.get("/organizations/{organization_id}/curriculum-subjects", response_model=list[CurriculumSubjectResponse])
def list_curriculum_subjects(
    organization_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[CurriculumSubject]:
    return curriculum_service.list_curriculum_subjects(db, user, organization_id)


@router.post(
    "/organizations/{organization_id}/curriculum-subjects",
    response_model=CurriculumSubjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_curriculum_subject(
    organization_id: uuid.UUID,
    payload: CurriculumSubjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CurriculumSubject:
    return curriculum_service.create_curriculum_subject(db, user, organization_id, payload)


@router.delete(
    "/organizations/{organization_id}/curriculum-subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_curriculum_subject(
    organization_id: uuid.UUID, subject_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    curriculum_service.delete_curriculum_subject(db, user, organization_id, subject_id)


@router.get("/organizations/{organization_id}/activity", response_model=list[ActivityLogResponse])
def get_activity(
    organization_id: uuid.UUID,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    return activity_service.list_activity(db, user, organization_id, limit=limit)


@router.get("/organizations/{organization_id}/teacher-overview", response_model=list[TeacherOverviewRow])
def get_teacher_overview(
    organization_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[TeacherOverviewRow]:
    return school_service.get_teacher_overview(db, user, organization_id)


@router.get("/organizations/{organization_id}/weekly-overview", response_model=WeeklyPlanDetail)
def get_weekly_overview(
    organization_id: uuid.UUID,
    teacher_user_id: uuid.UUID,
    week_start_date: date,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WeeklyPlanDetail:
    plan = weekly_plan_service.get_weekly_plan_for_admin(db, user, organization_id, teacher_user_id, week_start_date)
    items, issues = weekly_plan_service.get_weekly_plan_items_and_issues_unchecked(db, plan.id)
    return WeeklyPlanDetail(
        id=plan.id,
        organization_id=plan.organization_id,
        teacher_user_id=plan.teacher_user_id,
        week_start_date=plan.week_start_date,
        created_at=plan.created_at,
        items=items,
        issues=issues,
    )
