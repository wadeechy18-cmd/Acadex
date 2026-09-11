import uuid
from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.weekly_plan import WeeklyPlan
from app.schemas.weekly_plan import (
    WeeklyPlanCreate,
    WeeklyPlanDetail,
    WeeklyPlanItemCreate,
    WeeklyPlanItemUpdate,
    WeeklyPlanItemView,
)
from app.services import weekly_plan_service

router = APIRouter(tags=["weekly-plans"])


def _to_detail(db: Session, plan: WeeklyPlan, user: User) -> WeeklyPlanDetail:
    items, issues = weekly_plan_service.get_weekly_plan_items_and_issues(db, user, plan.id)
    return WeeklyPlanDetail(
        id=plan.id,
        organization_id=plan.organization_id,
        teacher_user_id=plan.teacher_user_id,
        week_start_date=plan.week_start_date,
        created_at=plan.created_at,
        items=items,
        issues=issues,
    )


@router.post(
    "/organizations/{organization_id}/weekly-plans", response_model=WeeklyPlanDetail, status_code=status.HTTP_201_CREATED
)
def create_or_get_weekly_plan(
    organization_id: uuid.UUID,
    payload: WeeklyPlanCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WeeklyPlanDetail:
    plan = weekly_plan_service.get_or_create_weekly_plan(db, user, organization_id, payload.week_start_date)
    return _to_detail(db, plan, user)


@router.get("/organizations/{organization_id}/weekly-plans", response_model=WeeklyPlanDetail)
def get_weekly_plan_by_week(
    organization_id: uuid.UUID,
    week_start_date: date,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WeeklyPlanDetail:
    plan = weekly_plan_service.get_weekly_plan_by_week(db, user, organization_id, week_start_date)
    return _to_detail(db, plan, user)


@router.get("/weekly-plans/{weekly_plan_id}", response_model=WeeklyPlanDetail)
def get_weekly_plan(
    weekly_plan_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> WeeklyPlanDetail:
    plan = weekly_plan_service.get_weekly_plan(db, user, weekly_plan_id)
    return _to_detail(db, plan, user)


@router.delete("/weekly-plans/{weekly_plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_weekly_plan(
    weekly_plan_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    weekly_plan_service.delete_weekly_plan(db, user, weekly_plan_id)


@router.post(
    "/weekly-plans/{weekly_plan_id}/items", response_model=WeeklyPlanItemView, status_code=status.HTTP_201_CREATED
)
def add_weekly_plan_item(
    weekly_plan_id: uuid.UUID,
    payload: WeeklyPlanItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WeeklyPlanItemView:
    item = weekly_plan_service.add_item(db, user, weekly_plan_id, payload)
    return weekly_plan_service.build_item_views(db, [item])[0]


@router.patch("/weekly-plan-items/{item_id}", response_model=WeeklyPlanItemView)
def update_weekly_plan_item(
    item_id: uuid.UUID,
    payload: WeeklyPlanItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WeeklyPlanItemView:
    item = weekly_plan_service.update_item(db, user, item_id, payload)
    return weekly_plan_service.build_item_views(db, [item])[0]


@router.delete("/weekly-plan-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_weekly_plan_item(
    item_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    weekly_plan_service.delete_item(db, user, item_id)
