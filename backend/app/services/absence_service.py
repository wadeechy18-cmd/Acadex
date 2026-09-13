import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.absence import AffectedLesson, TeacherAbsence
from app.models.school import SchoolMembershipRole
from app.models.timetable import AcademicYear, TimeSlot, Timetable, TimetableEntry
from app.models.user import User
from app.services import audit_service, school_service


def _compute_affected_entries(db: Session, school_id: uuid.UUID, teacher_user_id: uuid.UUID, absence_date: date) -> list[TimetableEntry]:
    """Deterministic, no AI: every TimetableEntry for this teacher whose
    TimeSlot falls on this date's weekday, on any timetable whose academic
    year actually covers this date. A weekend date matches no TimeSlot
    (they only span Monday-Friday), so it correctly yields no lessons.
    """
    day_of_week = absence_date.weekday()

    timetables = (
        db.query(Timetable)
        .join(AcademicYear, AcademicYear.id == Timetable.academic_year_id)
        .filter(Timetable.school_id == school_id, AcademicYear.start_date <= absence_date, AcademicYear.end_date >= absence_date)
        .all()
    )
    if not timetables:
        return []

    timetable_ids = [t.id for t in timetables]
    return (
        db.query(TimetableEntry)
        .join(TimeSlot, TimeSlot.id == TimetableEntry.time_slot_id)
        .filter(
            TimetableEntry.timetable_id.in_(timetable_ids),
            TimetableEntry.teacher_user_id == teacher_user_id,
            TimeSlot.day_of_week == day_of_week,
        )
        .all()
    )


def report_absence(db: Session, actor: User, school_id: uuid.UUID, teacher_user_id: uuid.UUID, absence_date: date, reason: str | None) -> TeacherAbsence:
    school_service.assert_school_member(db, actor, school_id, min_role=SchoolMembershipRole.ADMIN)

    teacher = db.get(User, teacher_user_id)
    if not teacher or not school_service.get_membership(db, teacher, school_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The teacher must be a member of this school.")

    existing = db.query(TeacherAbsence).filter_by(school_id=school_id, teacher_user_id=teacher_user_id, date=absence_date).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "An absence has already been reported for this teacher on this date.")

    absence = TeacherAbsence(school_id=school_id, teacher_user_id=teacher_user_id, date=absence_date, reason=reason, reported_by_user_id=actor.id)
    db.add(absence)
    db.flush()

    for entry in _compute_affected_entries(db, school_id, teacher_user_id, absence_date):
        db.add(AffectedLesson(teacher_absence_id=absence.id, timetable_entry_id=entry.id))

    audit_service.log(db, actor, school_id, "absence.report", {"teacher_user_id": str(teacher_user_id), "date": absence_date.isoformat()})
    db.commit()
    db.refresh(absence)
    return absence


def list_absences(db: Session, actor: User, school_id: uuid.UUID, on_date: date | None = None) -> list[TeacherAbsence]:
    school_service.assert_school_member(db, actor, school_id, min_role=SchoolMembershipRole.ADMIN)
    query = db.query(TeacherAbsence).filter_by(school_id=school_id)
    if on_date:
        query = query.filter_by(date=on_date)
    return query.order_by(TeacherAbsence.date.desc()).all()


def get_absence(db: Session, actor: User, school_id: uuid.UUID, absence_id: uuid.UUID) -> TeacherAbsence:
    school_service.assert_school_member(db, actor, school_id, min_role=SchoolMembershipRole.ADMIN)
    absence = db.query(TeacherAbsence).filter_by(id=absence_id, school_id=school_id).first()
    if not absence:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Absence not found.")
    return absence


def list_affected_lessons(db: Session, absence: TeacherAbsence) -> list[AffectedLesson]:
    return db.query(AffectedLesson).filter_by(teacher_absence_id=absence.id).all()


def delete_absence(db: Session, actor: User, school_id: uuid.UUID, absence_id: uuid.UUID) -> None:
    absence = get_absence(db, actor, school_id, absence_id)
    db.delete(absence)
    audit_service.log(db, actor, school_id, "absence.delete", {"absence_id": str(absence_id)})
    db.commit()
