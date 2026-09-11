import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.lesson_plan import LessonPlan, LessonPlanVersion
from app.models.user import User
from app.planning.templates import build_sections_from_template
from app.planning.validator import LessonPlanQualityReport, validate_lesson_plan
from app.schemas.lesson_plan import LessonPlanContent, LessonPlanCreate, LessonPlanUpdate
from app.services.planner_class_service import assert_can_manage_class, get_class


def get_latest_version_number(db: Session, lesson_plan_id: uuid.UUID) -> int:
    row = (
        db.query(LessonPlanVersion.version_number)
        .filter_by(lesson_plan_id=lesson_plan_id)
        .order_by(LessonPlanVersion.version_number.desc())
        .first()
    )
    return row[0] if row else 0


def get_latest_version(db: Session, lesson_plan_id: uuid.UUID) -> LessonPlanVersion:
    version = (
        db.query(LessonPlanVersion)
        .filter_by(lesson_plan_id=lesson_plan_id)
        .order_by(LessonPlanVersion.version_number.desc())
        .first()
    )
    if not version:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson plan has no saved content.")
    return version


def create_lesson_plan(db: Session, user: User, class_id: uuid.UUID, payload: LessonPlanCreate) -> LessonPlan:
    # Only the class's own teacher may create lesson plans for it -- reuses
    # the same ownership check classes already enforce.
    teaching_class = assert_can_manage_class(db, user, class_id)

    lesson_plan = LessonPlan(
        organization_id=teaching_class.organization_id,
        class_id=teaching_class.id,
        teacher_user_id=user.id,
        title=payload.title,
        topic=payload.topic,
        duration_minutes=payload.duration_minutes,
        template_type=payload.template_type,
    )
    db.add(lesson_plan)
    db.flush()

    initial_content = LessonPlanContent(
        sections=build_sections_from_template(payload.template_type, payload.duration_minutes)
    )
    db.add(
        LessonPlanVersion(
            lesson_plan_id=lesson_plan.id,
            version_number=1,
            content=initial_content.model_dump(mode="json"),
            created_by_user_id=user.id,
        )
    )
    db.commit()
    db.refresh(lesson_plan)
    return lesson_plan


def list_lesson_plans(db: Session, user: User, class_id: uuid.UUID) -> list[LessonPlan]:
    # get_class already asserts the caller is a member of the class's
    # organization -- viewing plan metadata follows the same visibility as
    # viewing the class itself (see planner_class_service.list_classes).
    get_class(db, user, class_id)
    return db.query(LessonPlan).filter_by(class_id=class_id).order_by(LessonPlan.created_at.desc()).all()


def get_lesson_plan(db: Session, user: User, lesson_plan_id: uuid.UUID) -> LessonPlan:
    lesson_plan = db.get(LessonPlan, lesson_plan_id)
    if not lesson_plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson plan not found.")
    get_class(db, user, lesson_plan.class_id)  # raises 403 if not an org member
    return lesson_plan


def get_quality_report(db: Session, user: User, lesson_plan_id: uuid.UUID) -> LessonPlanQualityReport:
    lesson_plan = get_lesson_plan(db, user, lesson_plan_id)
    latest = get_latest_version(db, lesson_plan.id)
    content = LessonPlanContent.model_validate(latest.content)
    return validate_lesson_plan(
        title=lesson_plan.title,
        topic=lesson_plan.topic,
        duration_minutes=lesson_plan.duration_minutes,
        template_type=lesson_plan.template_type,
        content=content,
    )


def get_draft_quality_report(
    db: Session, user: User, lesson_plan_id: uuid.UUID, *, title: str, topic: str,
    duration_minutes: int, template_type, content: LessonPlanContent,
) -> LessonPlanQualityReport:
    get_lesson_plan(db, user, lesson_plan_id)  # membership check only -- ignores persisted content
    return validate_lesson_plan(
        title=title, topic=topic, duration_minutes=duration_minutes, template_type=template_type, content=content
    )


def assert_can_manage_lesson_plan(db: Session, user: User, lesson_plan_id: uuid.UUID) -> LessonPlan:
    lesson_plan = get_lesson_plan(db, user, lesson_plan_id)
    if lesson_plan.teacher_user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the teacher who owns this lesson plan can modify it.")
    return lesson_plan


def update_lesson_plan(db: Session, user: User, lesson_plan_id: uuid.UUID, payload: LessonPlanUpdate) -> LessonPlan:
    lesson_plan = assert_can_manage_lesson_plan(db, user, lesson_plan_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lesson_plan, field, value)
    db.commit()
    db.refresh(lesson_plan)
    return lesson_plan


def save_content(db: Session, user: User, lesson_plan_id: uuid.UUID, content: LessonPlanContent) -> LessonPlanVersion:
    lesson_plan = assert_can_manage_lesson_plan(db, user, lesson_plan_id)
    latest = get_latest_version(db, lesson_plan.id)

    version = LessonPlanVersion(
        lesson_plan_id=lesson_plan.id,
        version_number=latest.version_number + 1,
        content=content.model_dump(mode="json"),
        created_by_user_id=user.id,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def list_versions(db: Session, user: User, lesson_plan_id: uuid.UUID) -> list[LessonPlanVersion]:
    get_lesson_plan(db, user, lesson_plan_id)  # view access, same as the plan itself
    return (
        db.query(LessonPlanVersion)
        .filter_by(lesson_plan_id=lesson_plan_id)
        .order_by(LessonPlanVersion.version_number.desc())
        .all()
    )


def restore_version(db: Session, user: User, lesson_plan_id: uuid.UUID, version_id: uuid.UUID) -> LessonPlanVersion:
    """Restoring never deletes history -- it appends a new version whose
    content matches the chosen old one, so the version log stays a complete,
    append-only record of every save.
    """
    lesson_plan = assert_can_manage_lesson_plan(db, user, lesson_plan_id)
    old_version = db.query(LessonPlanVersion).filter_by(id=version_id, lesson_plan_id=lesson_plan.id).first()
    if not old_version:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Version not found.")

    latest = get_latest_version(db, lesson_plan.id)
    new_version = LessonPlanVersion(
        lesson_plan_id=lesson_plan.id,
        version_number=latest.version_number + 1,
        content=old_version.content,
        created_by_user_id=user.id,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version


def duplicate_lesson_plan(db: Session, user: User, lesson_plan_id: uuid.UUID) -> LessonPlan:
    source = assert_can_manage_lesson_plan(db, user, lesson_plan_id)
    source_content = get_latest_version(db, source.id).content

    copy = LessonPlan(
        organization_id=source.organization_id,
        class_id=source.class_id,
        teacher_user_id=user.id,
        title=f"{source.title} (Copy)",
        topic=source.topic,
        duration_minutes=source.duration_minutes,
        template_type=source.template_type,
    )
    db.add(copy)
    db.flush()

    db.add(
        LessonPlanVersion(
            lesson_plan_id=copy.id,
            version_number=1,
            content=source_content,
            created_by_user_id=user.id,
        )
    )
    db.commit()
    db.refresh(copy)
    return copy


def delete_lesson_plan(db: Session, user: User, lesson_plan_id: uuid.UUID) -> None:
    lesson_plan = assert_can_manage_lesson_plan(db, user, lesson_plan_id)
    db.delete(lesson_plan)
    db.commit()
