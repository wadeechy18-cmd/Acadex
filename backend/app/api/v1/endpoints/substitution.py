import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.absence import AffectedLesson
from app.models.class_ import Class
from app.models.curriculum import Subject
from app.models.substitution import SubstitutionAssignment, SubstitutionPlan, TimetableException
from app.models.timetable import Room, TimeSlot, TimetableEntry
from app.models.user import User
from app.schemas.substitution import ReassignRequest, SubstitutionAssignmentResponse, SubstitutionPlanResponse, TimetableExceptionResponse
from app.services import auth_service, lesson_plan_service, substitution_service

school_router = APIRouter(prefix="/schools", tags=["substitution"])
my_cover_router = APIRouter(prefix="/timetable-exceptions", tags=["substitution"])


def _assignment_response(db: Session, assignment: SubstitutionAssignment) -> SubstitutionAssignmentResponse:
    affected = db.get(AffectedLesson, assignment.affected_lesson_id)
    entry = db.get(TimetableEntry, affected.timetable_entry_id)
    slot = db.get(TimeSlot, entry.time_slot_id)
    subject = db.get(Subject, entry.subject_id)
    substitute = db.get(User, assignment.substitute_teacher_user_id) if assignment.substitute_teacher_user_id else None
    return SubstitutionAssignmentResponse(
        id=assignment.id,
        affected_lesson_id=assignment.affected_lesson_id,
        subject_name=subject.name,
        time_slot_label=slot.label,
        status=assignment.status,
        substitute_teacher_user_id=assignment.substitute_teacher_user_id,
        substitute_teacher_name=auth_service.get_display_name(db, substitute) if substitute else None,
        reason=assignment.reason,
    )


def _plan_response(db: Session, plan: SubstitutionPlan) -> SubstitutionPlanResponse:
    approver = db.get(User, plan.approved_by_user_id) if plan.approved_by_user_id else None
    return SubstitutionPlanResponse(
        id=plan.id,
        teacher_absence_id=plan.teacher_absence_id,
        status=plan.status,
        assignments=[_assignment_response(db, a) for a in substitution_service.list_assignments(db, plan)],
        approved_by_name=auth_service.get_display_name(db, approver) if approver else None,
        approved_at=plan.approved_at,
        created_at=plan.created_at,
    )


@school_router.post("/{school_id}/absences/{absence_id}/substitution-plan/generate", response_model=SubstitutionPlanResponse, status_code=status.HTTP_201_CREATED)
def generate_plan(
    school_id: uuid.UUID, absence_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> SubstitutionPlanResponse:
    plan = substitution_service.generate_plan(db, user, school_id, absence_id)
    return _plan_response(db, plan)


@school_router.get("/{school_id}/absences/{absence_id}/substitution-plan", response_model=SubstitutionPlanResponse)
def get_plan(school_id: uuid.UUID, absence_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SubstitutionPlanResponse:
    plan = substitution_service.get_plan_for_absence(db, user, school_id, absence_id)
    return _plan_response(db, plan)


@school_router.patch("/{school_id}/substitution-assignments/{assignment_id}", response_model=SubstitutionAssignmentResponse)
def reassign(
    school_id: uuid.UUID, assignment_id: uuid.UUID, payload: ReassignRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> SubstitutionAssignmentResponse:
    assignment = substitution_service.reassign(db, user, school_id, assignment_id, payload.substitute_teacher_user_id)
    return _assignment_response(db, assignment)


@school_router.post("/{school_id}/substitution-plans/{plan_id}/approve", response_model=SubstitutionPlanResponse)
def approve_plan(school_id: uuid.UUID, plan_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SubstitutionPlanResponse:
    plan = substitution_service.approve_plan(db, user, school_id, plan_id)
    return _plan_response(db, plan)


@school_router.post("/{school_id}/substitution-plans/{plan_id}/reject", response_model=SubstitutionPlanResponse)
def reject_plan(school_id: uuid.UUID, plan_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SubstitutionPlanResponse:
    plan = substitution_service.reject_plan(db, user, school_id, plan_id)
    return _plan_response(db, plan)


def _exception_response(db: Session, exception: TimetableException, include_cover_lesson: bool) -> TimetableExceptionResponse:
    entry = db.get(TimetableEntry, exception.timetable_entry_id)
    slot = db.get(TimeSlot, entry.time_slot_id)
    subject = db.get(Subject, entry.subject_id)
    class_ = db.get(Class, entry.class_id) if entry.class_id else None
    room = db.get(Room, entry.room_id) if entry.room_id else None
    original_teacher = db.get(User, entry.teacher_user_id)
    substitute = db.get(User, exception.substitute_teacher_user_id) if exception.substitute_teacher_user_id else None

    response = TimetableExceptionResponse(
        id=exception.id,
        date=exception.date.isoformat(),
        timetable_entry_id=entry.id,
        subject_name=subject.name,
        time_slot_label=slot.label,
        class_name=class_.name if class_ else None,
        room_name=room.name if room else None,
        original_teacher_name=auth_service.get_display_name(db, original_teacher),
        substitute_teacher_user_id=exception.substitute_teacher_user_id,
        substitute_teacher_name=auth_service.get_display_name(db, substitute) if substitute else None,
    )

    if include_cover_lesson:
        lesson_plan = substitution_service.find_cover_lesson_plan(db, entry)
        response.cover_lesson_plan_id = lesson_plan.id if lesson_plan else None
        response.cover_lesson_plan_title = None
        if lesson_plan:
            current = lesson_plan_service.get_current_version(db, lesson_plan)
            response.cover_lesson_plan_title = current.content.get("title")
            response.cover_lesson_plan_message = f"Showing {original_teacher.email.split('@')[0]}'s lesson plan for this class."
        else:
            response.cover_lesson_plan_message = "No matching lesson plan was found. Contact the original teacher or create one."

    return response


@my_cover_router.get("/mine", response_model=list[TimetableExceptionResponse])
def list_my_cover_lessons(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[TimetableExceptionResponse]:
    exceptions = db.query(TimetableException).filter_by(substitute_teacher_user_id=user.id).order_by(TimetableException.date.desc()).all()
    return [_exception_response(db, e, include_cover_lesson=True) for e in exceptions]
