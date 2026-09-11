import uuid
from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.lesson_plan import LessonPlan
from app.models.organization import OrganizationRole
from app.models.planner_class import TeachingClass
from app.models.user import User
from app.models.weekly_plan import WeeklyPlan, WeeklyPlanItem
from app.planning.weekly_planner import analyze_week
from app.schemas.weekly_plan import WeeklyPlanIssue, WeeklyPlanItemCreate, WeeklyPlanItemUpdate, WeeklyPlanItemView
from app.services.organization_service import assert_org_member


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def get_or_create_weekly_plan(db: Session, user: User, organization_id: uuid.UUID, week_start_date: date) -> WeeklyPlan:
    """A weekly plan is always the calling teacher's own timetable -- there is
    no "create a plan for someone else" here, the same way a personal
    organization is always your own (see organization_service).
    """
    assert_org_member(db, user, organization_id, min_role=OrganizationRole.TEACHER)
    monday = _monday_of(week_start_date)

    existing = (
        db.query(WeeklyPlan)
        .filter_by(organization_id=organization_id, teacher_user_id=user.id, week_start_date=monday)
        .first()
    )
    if existing:
        return existing

    plan = WeeklyPlan(organization_id=organization_id, teacher_user_id=user.id, week_start_date=monday)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def get_weekly_plan_by_week(db: Session, user: User, organization_id: uuid.UUID, week_start_date: date) -> WeeklyPlan:
    assert_org_member(db, user, organization_id, min_role=OrganizationRole.TEACHER)
    monday = _monday_of(week_start_date)

    plan = (
        db.query(WeeklyPlan)
        .filter_by(organization_id=organization_id, teacher_user_id=user.id, week_start_date=monday)
        .first()
    )
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No weekly plan exists for that week yet.")
    return plan


def get_weekly_plan(db: Session, user: User, weekly_plan_id: uuid.UUID) -> WeeklyPlan:
    """Weekly plans are personal, not org-shared: only the owning teacher can
    view or manage their own timetable. Cross-teacher visibility for school
    admins is a Phase 9 concern (a dedicated read-only overview), not this.
    """
    plan = db.get(WeeklyPlan, weekly_plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Weekly plan not found.")
    if plan.teacher_user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This isn't your weekly plan.")
    return plan


def delete_weekly_plan(db: Session, user: User, weekly_plan_id: uuid.UUID) -> None:
    plan = get_weekly_plan(db, user, weekly_plan_id)
    db.delete(plan)
    db.commit()


def _class_for_item(db: Session, weekly_plan: WeeklyPlan, class_id: uuid.UUID) -> TeachingClass:
    teaching_class = db.get(TeachingClass, class_id)
    if not teaching_class:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Class not found.")
    if teaching_class.organization_id != weekly_plan.organization_id or teaching_class.teacher_user_id != weekly_plan.teacher_user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That class isn't one of yours in this workspace.")
    return teaching_class


def _lesson_plan_for_item(db: Session, class_id: uuid.UUID, lesson_plan_id: uuid.UUID) -> LessonPlan:
    lesson_plan = db.get(LessonPlan, lesson_plan_id)
    if not lesson_plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson plan not found.")
    if lesson_plan.class_id != class_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That lesson plan belongs to a different class.")
    return lesson_plan


def add_item(db: Session, user: User, weekly_plan_id: uuid.UUID, payload: WeeklyPlanItemCreate) -> WeeklyPlanItem:
    plan = get_weekly_plan(db, user, weekly_plan_id)
    _class_for_item(db, plan, payload.class_id)
    if payload.lesson_plan_id:
        _lesson_plan_for_item(db, payload.class_id, payload.lesson_plan_id)

    item = WeeklyPlanItem(weekly_plan_id=plan.id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_item(db: Session, user: User, item_id: uuid.UUID) -> WeeklyPlanItem:
    item = db.get(WeeklyPlanItem, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found.")
    get_weekly_plan(db, user, item.weekly_plan_id)  # ownership check
    return item


def update_item(db: Session, user: User, item_id: uuid.UUID, payload: WeeklyPlanItemUpdate) -> WeeklyPlanItem:
    item = get_item(db, user, item_id)
    plan = db.get(WeeklyPlan, item.weekly_plan_id)

    updates = payload.model_dump(exclude_unset=True)
    class_id = updates.get("class_id", item.class_id)
    if "class_id" in updates:
        _class_for_item(db, plan, class_id)
    if "lesson_plan_id" in updates and updates["lesson_plan_id"] is not None:
        _lesson_plan_for_item(db, class_id, updates["lesson_plan_id"])

    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, user: User, item_id: uuid.UUID) -> None:
    item = get_item(db, user, item_id)
    db.delete(item)
    db.commit()


def build_item_views(db: Session, items: list[WeeklyPlanItem]) -> list[WeeklyPlanItemView]:
    if not items:
        return []

    class_ids = {i.class_id for i in items}
    classes = {c.id: c for c in db.query(TeachingClass).filter(TeachingClass.id.in_(class_ids)).all()}

    lesson_plan_ids = {i.lesson_plan_id for i in items if i.lesson_plan_id}
    lesson_plans = {}
    if lesson_plan_ids:
        lesson_plans = {lp.id: lp for lp in db.query(LessonPlan).filter(LessonPlan.id.in_(lesson_plan_ids)).all()}

    views = []
    for item in items:
        lesson_plan = lesson_plans.get(item.lesson_plan_id) if item.lesson_plan_id else None
        views.append(
            WeeklyPlanItemView(
                id=item.id,
                class_id=item.class_id,
                class_name=classes[item.class_id].name,
                lesson_plan_id=item.lesson_plan_id,
                topic=lesson_plan.topic if lesson_plan else item.topic_override,
                template_type=lesson_plan.template_type.value if lesson_plan else None,
                day_of_week=item.day_of_week,
                start_time=item.start_time,
                duration_minutes=item.duration_minutes,
            )
        )
    return views


def get_weekly_plan_items_and_issues(
    db: Session, user: User, weekly_plan_id: uuid.UUID
) -> tuple[list[WeeklyPlanItemView], list[WeeklyPlanIssue]]:
    get_weekly_plan(db, user, weekly_plan_id)  # ownership check
    items = db.query(WeeklyPlanItem).filter_by(weekly_plan_id=weekly_plan_id).order_by(WeeklyPlanItem.start_time).all()
    views = build_item_views(db, items)
    return views, analyze_week(views)
