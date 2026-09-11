import uuid

from sqlalchemy.orm import Session

from app.models.lesson_plan import LessonPlan
from app.models.organization import OrganizationRole
from app.models.planner_class import TeachingClass
from app.models.user import User
from app.schemas.school import TeacherOverviewRow
from app.services.auth_service import get_display_name
from app.services.organization_service import assert_org_member, list_members


def get_teacher_overview(db: Session, user: User, organization_id: uuid.UUID) -> list[TeacherOverviewRow]:
    assert_org_member(db, user, organization_id, min_role=OrganizationRole.ADMIN)
    members = list_members(db, user, organization_id)

    rows = []
    for member in members:
        member_user = db.get(User, member.user_id)
        if not member_user:
            continue
        class_count = (
            db.query(TeachingClass)
            .filter_by(organization_id=organization_id, teacher_user_id=member.user_id)
            .count()
        )
        lesson_plan_count = (
            db.query(LessonPlan)
            .filter_by(organization_id=organization_id, teacher_user_id=member.user_id)
            .count()
        )
        rows.append(
            TeacherOverviewRow(
                user_id=member.user_id,
                display_name=get_display_name(db, member_user),
                email=member_user.email,
                role=member.role,
                class_count=class_count,
                lesson_plan_count=lesson_plan_count,
            )
        )
    return rows
