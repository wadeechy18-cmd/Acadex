import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.absence import AffectedLesson, TeacherAbsence
from app.models.class_ import Class
from app.models.curriculum import Subject
from app.models.school import SchoolMembership, SchoolMembershipRole
from app.models.substitution import AssignmentStatus, Notification, SubstitutionAssignment, SubstitutionPlan, SubstitutionPlanStatus, TimetableException
from app.models.timetable import AvailabilityStatus, TeacherAvailability, TeacherSubjectQualification, TimeSlot, TimetableEntry
from app.models.lesson_plan import LessonPlan
from app.models.user import User
from app.planning.substitution_optimizer import CoverCandidate, LessonToCover, optimize_substitutions
from app.services import absence_service, audit_service, auth_service, school_service

_RECENT_COVER_WINDOW_DAYS = 30


def _school_teacher_ids(db: Session, school_id: uuid.UUID) -> list[uuid.UUID]:
    memberships = db.query(SchoolMembership).filter_by(school_id=school_id, role=SchoolMembershipRole.TEACHER).all()
    return [m.user_id for m in memberships]


def _build_candidates(db: Session, school_id: uuid.UUID, absent_teacher_id: uuid.UUID, entry: TimetableEntry, slot: TimeSlot) -> list[CoverCandidate]:
    teacher_ids = [t for t in _school_teacher_ids(db, school_id) if t != absent_teacher_id]
    if not teacher_ids:
        return []

    unavailable_ids = {
        a.teacher_user_id
        for a in db.query(TeacherAvailability).filter(
            TeacherAvailability.school_id == school_id,
            TeacherAvailability.time_slot_id == slot.id,
            TeacherAvailability.status == AvailabilityStatus.UNAVAILABLE,
        )
    }
    busy_ids = {
        e.teacher_user_id
        for e in db.query(TimetableEntry).filter(TimetableEntry.time_slot_id == slot.id, TimetableEntry.teacher_user_id.in_(teacher_ids))
    }
    qualified_ids = {
        q.teacher_user_id
        for q in db.query(TeacherSubjectQualification).filter_by(school_id=school_id, subject_id=entry.subject_id)
    }

    recent_since = date.today() - timedelta(days=_RECENT_COVER_WINDOW_DAYS)
    recent_cover_counts: dict[uuid.UUID, int] = {}
    recent_assignments = (
        db.query(SubstitutionAssignment)
        .join(TimetableException, TimetableException.substitution_plan_id == SubstitutionAssignment.substitution_plan_id)
        .filter(
            SubstitutionAssignment.status == AssignmentStatus.ASSIGNED,
            TimetableException.school_id == school_id,
            TimetableException.date >= recent_since,
        )
        .all()
    )
    for a in recent_assignments:
        if a.substitute_teacher_user_id:
            recent_cover_counts[a.substitute_teacher_user_id] = recent_cover_counts.get(a.substitute_teacher_user_id, 0) + 1

    workload_counts: dict[uuid.UUID, int] = {}
    for e in db.query(TimetableEntry).join(TimeSlot, TimeSlot.id == TimetableEntry.time_slot_id).filter(
        TimeSlot.day_of_week == slot.day_of_week, TimetableEntry.teacher_user_id.in_(teacher_ids)
    ):
        workload_counts[e.teacher_user_id] = workload_counts.get(e.teacher_user_id, 0) + 1

    candidates = []
    for teacher_id in teacher_ids:
        if teacher_id in unavailable_ids or teacher_id in busy_ids:
            continue
        candidates.append(
            CoverCandidate(
                teacher_user_id=str(teacher_id),
                is_qualified=teacher_id in qualified_ids,
                workload_today=workload_counts.get(teacher_id, 0),
                recent_cover_count=recent_cover_counts.get(teacher_id, 0),
            )
        )
    return candidates


def generate_plan(db: Session, actor: User, school_id: uuid.UUID, absence_id: uuid.UUID) -> SubstitutionPlan:
    absence = absence_service.get_absence(db, actor, school_id, absence_id)
    affected_lessons = absence_service.list_affected_lessons(db, absence)

    existing = db.query(SubstitutionPlan).filter_by(teacher_absence_id=absence.id).first()
    if existing:
        db.delete(existing)
        db.flush()

    plan = SubstitutionPlan(teacher_absence_id=absence.id, status=SubstitutionPlanStatus.PROPOSED)
    db.add(plan)
    db.flush()

    lessons: list[LessonToCover] = []
    candidates_by_lesson: dict[str, list[CoverCandidate]] = {}
    entries_by_id: dict[str, TimetableEntry] = {}

    for affected in affected_lessons:
        entry = db.get(TimetableEntry, affected.timetable_entry_id)
        slot = db.get(TimeSlot, entry.time_slot_id)
        lesson_key = str(affected.id)
        lessons.append(LessonToCover(affected_lesson_id=lesson_key, time_slot_id=str(slot.id)))
        candidates_by_lesson[lesson_key] = _build_candidates(db, school_id, absence.teacher_user_id, entry, slot)
        entries_by_id[lesson_key] = entry

    results = optimize_substitutions(lessons, candidates_by_lesson)

    for result in results:
        affected_id = uuid.UUID(result.affected_lesson_id)
        if result.teacher_user_id:
            db.add(
                SubstitutionAssignment(
                    substitution_plan_id=plan.id,
                    affected_lesson_id=affected_id,
                    status=AssignmentStatus.ASSIGNED,
                    substitute_teacher_user_id=uuid.UUID(result.teacher_user_id),
                )
            )
        else:
            db.add(
                SubstitutionAssignment(
                    substitution_plan_id=plan.id,
                    affected_lesson_id=affected_id,
                    status=AssignmentStatus.UNFILLED,
                    reason=result.unfilled_reason,
                )
            )

    db.commit()
    db.refresh(plan)
    return plan


def get_plan_for_absence(db: Session, actor: User, school_id: uuid.UUID, absence_id: uuid.UUID) -> SubstitutionPlan:
    absence = absence_service.get_absence(db, actor, school_id, absence_id)
    plan = db.query(SubstitutionPlan).filter_by(teacher_absence_id=absence.id).first()
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No substitution plan has been generated for this absence yet.")
    return plan


def _get_owned_plan(db: Session, actor: User, school_id: uuid.UUID, plan_id: uuid.UUID) -> SubstitutionPlan:
    school_service.assert_school_member(db, actor, school_id, min_role=SchoolMembershipRole.ADMIN)
    plan = db.get(SubstitutionPlan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Substitution plan not found.")
    absence = db.get(TeacherAbsence, plan.teacher_absence_id)
    if not absence or absence.school_id != school_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Substitution plan not found.")
    return plan


def list_assignments(db: Session, plan: SubstitutionPlan) -> list[SubstitutionAssignment]:
    return db.query(SubstitutionAssignment).filter_by(substitution_plan_id=plan.id).all()


def reassign(db: Session, actor: User, school_id: uuid.UUID, assignment_id: uuid.UUID, new_teacher_id: uuid.UUID | None) -> SubstitutionAssignment:
    assignment = db.get(SubstitutionAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found.")
    plan = _get_owned_plan(db, actor, school_id, assignment.substitution_plan_id)
    if plan.status != SubstitutionPlanStatus.PROPOSED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only a proposed plan can be edited.")

    if new_teacher_id:
        absence = db.get(TeacherAbsence, plan.teacher_absence_id)
        teacher = db.get(User, new_teacher_id)
        if not teacher or not school_service.get_membership(db, teacher, school_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "The substitute must be a member of this school.")
        if new_teacher_id == absence.teacher_user_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "The absent teacher cannot cover their own lesson.")

        affected = db.get(AffectedLesson, assignment.affected_lesson_id)
        entry = db.get(TimetableEntry, affected.timetable_entry_id)
        conflicting = (
            db.query(TimetableEntry).filter(TimetableEntry.time_slot_id == entry.time_slot_id, TimetableEntry.teacher_user_id == new_teacher_id).first()
        )
        if conflicting:
            raise HTTPException(status.HTTP_409_CONFLICT, "This teacher already has a lesson at that time.")

        assignment.status = AssignmentStatus.ASSIGNED
        assignment.substitute_teacher_user_id = new_teacher_id
        assignment.reason = None
    else:
        assignment.status = AssignmentStatus.UNFILLED
        assignment.substitute_teacher_user_id = None
        assignment.reason = "Manually unassigned by school admin."

    audit_service.log(db, actor, school_id, "substitution_assignment.reassign", {"assignment_id": str(assignment_id), "new_teacher_id": str(new_teacher_id) if new_teacher_id else None})
    db.commit()
    db.refresh(assignment)
    return assignment


def approve_plan(db: Session, actor: User, school_id: uuid.UUID, plan_id: uuid.UUID) -> SubstitutionPlan:
    plan = _get_owned_plan(db, actor, school_id, plan_id)
    if plan.status != SubstitutionPlanStatus.PROPOSED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only a proposed plan can be approved.")

    absence = db.get(TeacherAbsence, plan.teacher_absence_id)
    assignments = list_assignments(db, plan)

    for assignment in assignments:
        affected = db.get(AffectedLesson, assignment.affected_lesson_id)
        exception = TimetableException(
            school_id=school_id,
            date=absence.date,
            timetable_entry_id=affected.timetable_entry_id,
            substitute_teacher_user_id=assignment.substitute_teacher_user_id,
            substitution_plan_id=plan.id,
        )
        db.add(exception)

        if assignment.substitute_teacher_user_id:
            entry = db.get(TimetableEntry, affected.timetable_entry_id)
            subject = db.get(Subject, entry.subject_id)
            db.add(
                Notification(
                    user_id=assignment.substitute_teacher_user_id,
                    title="You've been assigned cover",
                    body=f"You are covering {subject.name} on {absence.date.isoformat()}.",
                )
            )

    plan.status = SubstitutionPlanStatus.APPROVED
    plan.approved_by_user_id = actor.id
    plan.approved_at = datetime.now(timezone.utc)
    audit_service.log(db, actor, school_id, "substitution_plan.approve", {"plan_id": str(plan.id)})
    db.commit()
    db.refresh(plan)
    return plan


def reject_plan(db: Session, actor: User, school_id: uuid.UUID, plan_id: uuid.UUID) -> SubstitutionPlan:
    plan = _get_owned_plan(db, actor, school_id, plan_id)
    if plan.status != SubstitutionPlanStatus.PROPOSED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only a proposed plan can be rejected.")
    plan.status = SubstitutionPlanStatus.REJECTED
    audit_service.log(db, actor, school_id, "substitution_plan.reject", {"plan_id": str(plan.id)})
    db.commit()
    db.refresh(plan)
    return plan


def find_cover_lesson_plan(db: Session, entry: TimetableEntry) -> LessonPlan | None:
    """Best-effort match for the substitute's "Cover Lesson" view -- there
    is no direct link from a TimetableEntry to a LessonPlan (a lesson plan
    isn't formally scheduled to a specific date/period in this version),
    so this looks for the absent teacher's most recently updated lesson
    plan for the same subject and class as a reasonable stand-in.
    """
    query = db.query(LessonPlan).filter_by(owner_user_id=entry.teacher_user_id, subject_id=entry.subject_id)
    if entry.class_id:
        query = query.filter_by(class_id=entry.class_id)
    return query.order_by(LessonPlan.updated_at.desc()).first()
