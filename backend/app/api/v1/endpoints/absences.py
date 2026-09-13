import uuid
from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.absence import AffectedLesson, TeacherAbsence
from app.models.class_ import Class
from app.models.curriculum import Subject
from app.models.timetable import Room, TimeSlot, TimetableEntry
from app.models.user import User
from app.schemas.absence import AffectedLessonResponse, ReportAbsenceRequest, TeacherAbsenceResponse
from app.services import absence_service, auth_service

router = APIRouter(prefix="/schools", tags=["absences"])


def _affected_lesson_response(db: Session, affected: AffectedLesson) -> AffectedLessonResponse:
    entry = db.get(TimetableEntry, affected.timetable_entry_id)
    slot = db.get(TimeSlot, entry.time_slot_id)
    subject = db.get(Subject, entry.subject_id)
    class_ = db.get(Class, entry.class_id) if entry.class_id else None
    room = db.get(Room, entry.room_id) if entry.room_id else None
    return AffectedLessonResponse(
        id=affected.id,
        timetable_entry_id=entry.id,
        time_slot_label=slot.label,
        day_of_week=slot.day_of_week,
        start_time=slot.start_time.isoformat(),
        end_time=slot.end_time.isoformat(),
        subject_name=subject.name,
        class_name=class_.name if class_ else None,
        room_name=room.name if room else None,
    )


def _absence_response(db: Session, absence: TeacherAbsence) -> TeacherAbsenceResponse:
    teacher = db.get(User, absence.teacher_user_id)
    reporter = db.get(User, absence.reported_by_user_id)
    affected = absence_service.list_affected_lessons(db, absence)
    return TeacherAbsenceResponse(
        id=absence.id,
        teacher_user_id=absence.teacher_user_id,
        teacher_name=auth_service.get_display_name(db, teacher),
        date=absence.date,
        reason=absence.reason,
        reported_by_name=auth_service.get_display_name(db, reporter),
        affected_lessons=[_affected_lesson_response(db, a) for a in affected],
        created_at=absence.created_at,
    )


@router.post("/{school_id}/absences", response_model=TeacherAbsenceResponse, status_code=status.HTTP_201_CREATED)
def report_absence(
    school_id: uuid.UUID, payload: ReportAbsenceRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> TeacherAbsenceResponse:
    absence = absence_service.report_absence(db, user, school_id, payload.teacher_user_id, payload.date, payload.reason)
    return _absence_response(db, absence)


@router.get("/{school_id}/absences", response_model=list[TeacherAbsenceResponse])
def list_absences(
    school_id: uuid.UUID, on_date: date | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[TeacherAbsenceResponse]:
    return [_absence_response(db, a) for a in absence_service.list_absences(db, user, school_id, on_date)]


@router.get("/{school_id}/absences/{absence_id}", response_model=TeacherAbsenceResponse)
def get_absence(school_id: uuid.UUID, absence_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> TeacherAbsenceResponse:
    absence = absence_service.get_absence(db, user, school_id, absence_id)
    return _absence_response(db, absence)


@router.delete("/{school_id}/absences/{absence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_absence(school_id: uuid.UUID, absence_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    absence_service.delete_absence(db, user, school_id, absence_id)
