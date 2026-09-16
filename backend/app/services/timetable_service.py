import uuid
from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.class_ import Class
from app.models.curriculum import Subject
from app.models.school import SchoolMembershipRole
from app.models.timetable import (
    AcademicYear,
    AvailabilityStatus,
    ClassSubjectRequirement,
    Room,
    TeacherAvailability,
    TeacherSubjectQualification,
    TimeSlot,
    Timetable,
    TimetableEntry,
)
from app.models.user import User
from app.planning.timetable_generation import GenerationResult, Requirement, TimetableSlot
from app.planning.timetable_generation import generate_timetable as solve_timetable
from app.schemas.timetable import (
    AcademicYearCreateRequest,
    ClassSubjectRequirementCreateRequest,
    RoomCreateRequest,
    TimeSlotCreateRequest,
    TimetableCreateRequest,
    TimetableEntryUpsertRequest,
)
from app.services import audit_service, school_service


def _assert_admin(db: Session, actor: User, school_id: uuid.UUID) -> None:
    school_service.assert_school_member(db, actor, school_id, min_role=SchoolMembershipRole.ADMIN)


def _assert_member(db: Session, actor: User, school_id: uuid.UUID) -> None:
    school_service.assert_school_member(db, actor, school_id)


# --- Academic years -----------------------------------------------------


def create_academic_year(db: Session, actor: User, school_id: uuid.UUID, payload: AcademicYearCreateRequest) -> AcademicYear:
    _assert_admin(db, actor, school_id)
    year = AcademicYear(school_id=school_id, name=payload.name, start_date=payload.start_date, end_date=payload.end_date)
    db.add(year)
    db.commit()
    db.refresh(year)
    return year


def list_academic_years(db: Session, actor: User, school_id: uuid.UUID) -> list[AcademicYear]:
    _assert_member(db, actor, school_id)
    return db.query(AcademicYear).filter_by(school_id=school_id).order_by(AcademicYear.start_date).all()


# --- Rooms ----------------------------------------------------------------


def create_room(db: Session, actor: User, school_id: uuid.UUID, payload: RoomCreateRequest) -> Room:
    _assert_admin(db, actor, school_id)
    room = Room(school_id=school_id, name=payload.name, capacity=payload.capacity)
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def list_rooms(db: Session, actor: User, school_id: uuid.UUID) -> list[Room]:
    _assert_member(db, actor, school_id)
    return db.query(Room).filter_by(school_id=school_id).order_by(Room.name).all()


def delete_room(db: Session, actor: User, school_id: uuid.UUID, room_id: uuid.UUID) -> None:
    _assert_admin(db, actor, school_id)
    room = db.query(Room).filter_by(id=room_id, school_id=school_id).first()
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found.")
    db.delete(room)
    db.commit()


# --- Time slots -------------------------------------------------------------


def create_time_slot(db: Session, actor: User, school_id: uuid.UUID, payload: TimeSlotCreateRequest) -> TimeSlot:
    _assert_admin(db, actor, school_id)
    if payload.end_time <= payload.start_time:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "End time must be after start time.")
    existing = db.query(TimeSlot).filter_by(
        school_id=school_id, day_of_week=payload.day_of_week, start_time=payload.start_time, end_time=payload.end_time
    ).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "This time slot already exists.")
    slot = TimeSlot(
        school_id=school_id, day_of_week=payload.day_of_week, start_time=payload.start_time, end_time=payload.end_time, label=payload.label
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


def list_time_slots(db: Session, actor: User, school_id: uuid.UUID) -> list[TimeSlot]:
    _assert_member(db, actor, school_id)
    return db.query(TimeSlot).filter_by(school_id=school_id).order_by(TimeSlot.day_of_week, TimeSlot.start_time).all()


def delete_time_slot(db: Session, actor: User, school_id: uuid.UUID, time_slot_id: uuid.UUID) -> None:
    _assert_admin(db, actor, school_id)
    slot = db.query(TimeSlot).filter_by(id=time_slot_id, school_id=school_id).first()
    if not slot:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Time slot not found.")
    db.delete(slot)
    db.commit()


# --- Timetables & entries ----------------------------------------------------


def create_timetable(db: Session, actor: User, school_id: uuid.UUID, payload: TimetableCreateRequest) -> Timetable:
    _assert_admin(db, actor, school_id)
    year = db.query(AcademicYear).filter_by(id=payload.academic_year_id, school_id=school_id).first()
    if not year:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Academic year not found.")
    timetable = Timetable(school_id=school_id, academic_year_id=payload.academic_year_id, name=payload.name)
    db.add(timetable)
    db.commit()
    db.refresh(timetable)
    return timetable


def list_timetables(db: Session, actor: User, school_id: uuid.UUID) -> list[Timetable]:
    _assert_member(db, actor, school_id)
    return db.query(Timetable).filter_by(school_id=school_id).order_by(Timetable.name).all()


def get_timetable(db: Session, actor: User, school_id: uuid.UUID, timetable_id: uuid.UUID) -> Timetable:
    _assert_member(db, actor, school_id)
    timetable = db.query(Timetable).filter_by(id=timetable_id, school_id=school_id).first()
    if not timetable:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Timetable not found.")
    return timetable


def list_entries(db: Session, timetable: Timetable) -> list[TimetableEntry]:
    return db.query(TimetableEntry).filter_by(timetable_id=timetable.id).all()


def _check_conflicts(db: Session, timetable_id: uuid.UUID, payload: TimetableEntryUpsertRequest, exclude_entry_id: uuid.UUID | None) -> None:
    """The hard constraints: never double-book a teacher, class, or room in
    the same slot on the same timetable.
    """
    query = db.query(TimetableEntry).filter_by(timetable_id=timetable_id, time_slot_id=payload.time_slot_id)
    if exclude_entry_id:
        query = query.filter(TimetableEntry.id != exclude_entry_id)
    slot_entries = query.all()

    for entry in slot_entries:
        if entry.teacher_user_id == payload.teacher_user_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "This teacher is already teaching another class in this time slot.")
        if payload.class_id and entry.class_id == payload.class_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "This class already has a lesson in this time slot.")
        if payload.room_id and entry.room_id == payload.room_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "This room is already in use in this time slot.")


def _validate_entry_refs(db: Session, school_id: uuid.UUID, timetable: Timetable, payload: TimetableEntryUpsertRequest) -> None:
    slot = db.query(TimeSlot).filter_by(id=payload.time_slot_id, school_id=school_id).first()
    if not slot:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Time slot not found.")

    teacher = db.get(User, payload.teacher_user_id)
    if not teacher or not school_service.get_membership(db, teacher, school_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The teacher must be a member of this school.")

    if not db.get(Subject, payload.subject_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found.")

    if payload.class_id and not db.get(Class, payload.class_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Class not found.")

    if payload.room_id and not db.query(Room).filter_by(id=payload.room_id, school_id=school_id).first():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found.")


def create_entry(db: Session, actor: User, school_id: uuid.UUID, timetable_id: uuid.UUID, payload: TimetableEntryUpsertRequest) -> TimetableEntry:
    _assert_admin(db, actor, school_id)
    timetable = get_timetable(db, actor, school_id, timetable_id)
    _validate_entry_refs(db, school_id, timetable, payload)
    _check_conflicts(db, timetable.id, payload, exclude_entry_id=None)

    entry = TimetableEntry(
        timetable_id=timetable.id,
        time_slot_id=payload.time_slot_id,
        teacher_user_id=payload.teacher_user_id,
        subject_id=payload.subject_id,
        class_id=payload.class_id,
        room_id=payload.room_id,
    )
    db.add(entry)
    db.flush()
    audit_service.log(db, actor, school_id, "timetable_entry.create", {"entry_id": str(entry.id), "timetable_id": str(timetable_id)})
    db.commit()
    db.refresh(entry)
    return entry


def update_entry(
    db: Session, actor: User, school_id: uuid.UUID, timetable_id: uuid.UUID, entry_id: uuid.UUID, payload: TimetableEntryUpsertRequest
) -> TimetableEntry:
    _assert_admin(db, actor, school_id)
    timetable = get_timetable(db, actor, school_id, timetable_id)
    entry = db.query(TimetableEntry).filter_by(id=entry_id, timetable_id=timetable.id).first()
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Timetable entry not found.")

    _validate_entry_refs(db, school_id, timetable, payload)
    _check_conflicts(db, timetable.id, payload, exclude_entry_id=entry.id)

    entry.time_slot_id = payload.time_slot_id
    entry.teacher_user_id = payload.teacher_user_id
    entry.subject_id = payload.subject_id
    entry.class_id = payload.class_id
    entry.room_id = payload.room_id
    audit_service.log(db, actor, school_id, "timetable_entry.update", {"entry_id": str(entry.id)})
    db.commit()
    db.refresh(entry)
    return entry


def delete_entry(db: Session, actor: User, school_id: uuid.UUID, timetable_id: uuid.UUID, entry_id: uuid.UUID) -> None:
    _assert_admin(db, actor, school_id)
    timetable = get_timetable(db, actor, school_id, timetable_id)
    entry = db.query(TimetableEntry).filter_by(id=entry_id, timetable_id=timetable.id).first()
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Timetable entry not found.")
    db.delete(entry)
    audit_service.log(db, actor, school_id, "timetable_entry.delete", {"entry_id": str(entry_id)})
    db.commit()


# --- Qualifications -----------------------------------------------------


def add_qualification(db: Session, actor: User, school_id: uuid.UUID, teacher_user_id: uuid.UUID, subject_id: uuid.UUID) -> TeacherSubjectQualification:
    _assert_admin(db, actor, school_id)
    teacher = db.get(User, teacher_user_id)
    if not teacher or not school_service.get_membership(db, teacher, school_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The teacher must be a member of this school.")
    if not db.get(Subject, subject_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found.")
    existing = db.query(TeacherSubjectQualification).filter_by(school_id=school_id, teacher_user_id=teacher_user_id, subject_id=subject_id).first()
    if existing:
        return existing
    qualification = TeacherSubjectQualification(school_id=school_id, teacher_user_id=teacher_user_id, subject_id=subject_id)
    db.add(qualification)
    db.commit()
    db.refresh(qualification)
    return qualification


def list_qualifications(db: Session, actor: User, school_id: uuid.UUID, teacher_user_id: uuid.UUID) -> list[TeacherSubjectQualification]:
    _assert_member(db, actor, school_id)
    return db.query(TeacherSubjectQualification).filter_by(school_id=school_id, teacher_user_id=teacher_user_id).all()


def remove_qualification(db: Session, actor: User, school_id: uuid.UUID, qualification_id: uuid.UUID) -> None:
    _assert_admin(db, actor, school_id)
    qualification = db.query(TeacherSubjectQualification).filter_by(id=qualification_id, school_id=school_id).first()
    if not qualification:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Qualification not found.")
    db.delete(qualification)
    db.commit()


# --- Availability -------------------------------------------------------


def set_availability(
    db: Session, actor: User, school_id: uuid.UUID, teacher_user_id: uuid.UUID, time_slot_id: uuid.UUID, status_value: AvailabilityStatus
) -> TeacherAvailability:
    """A teacher may set their own availability; a school admin may set it
    for any teacher in their school (e.g. onboarding a part-time pattern).
    """
    membership = school_service.assert_school_member(db, actor, school_id)
    if actor.id != teacher_user_id and membership.role != SchoolMembershipRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only set your own availability.")

    slot = db.query(TimeSlot).filter_by(id=time_slot_id, school_id=school_id).first()
    if not slot:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Time slot not found.")

    record = db.query(TeacherAvailability).filter_by(school_id=school_id, teacher_user_id=teacher_user_id, time_slot_id=time_slot_id).first()
    if record:
        record.status = status_value
    else:
        record = TeacherAvailability(school_id=school_id, teacher_user_id=teacher_user_id, time_slot_id=time_slot_id, status=status_value)
        db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_availability(db: Session, actor: User, school_id: uuid.UUID, teacher_user_id: uuid.UUID) -> list[TeacherAvailability]:
    _assert_member(db, actor, school_id)
    return db.query(TeacherAvailability).filter_by(school_id=school_id, teacher_user_id=teacher_user_id).all()


# --- Class/subject requirements (input to auto-generation) --------------


def add_requirement(
    db: Session, actor: User, school_id: uuid.UUID, timetable_id: uuid.UUID, payload: ClassSubjectRequirementCreateRequest
) -> ClassSubjectRequirement:
    _assert_admin(db, actor, school_id)
    timetable = get_timetable(db, actor, school_id, timetable_id)
    if not db.get(Class, payload.class_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Class not found.")
    if not db.get(Subject, payload.subject_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found.")

    existing = db.query(ClassSubjectRequirement).filter_by(timetable_id=timetable.id, class_id=payload.class_id, subject_id=payload.subject_id).first()
    if existing:
        existing.periods_per_week = payload.periods_per_week
        db.commit()
        db.refresh(existing)
        return existing

    requirement = ClassSubjectRequirement(
        timetable_id=timetable.id, class_id=payload.class_id, subject_id=payload.subject_id, periods_per_week=payload.periods_per_week
    )
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return requirement


def list_requirements(db: Session, actor: User, school_id: uuid.UUID, timetable_id: uuid.UUID) -> list[ClassSubjectRequirement]:
    timetable = get_timetable(db, actor, school_id, timetable_id)
    return db.query(ClassSubjectRequirement).filter_by(timetable_id=timetable.id).all()


def delete_requirement(db: Session, actor: User, school_id: uuid.UUID, timetable_id: uuid.UUID, requirement_id: uuid.UUID) -> None:
    _assert_admin(db, actor, school_id)
    timetable = get_timetable(db, actor, school_id, timetable_id)
    requirement = db.query(ClassSubjectRequirement).filter_by(id=requirement_id, timetable_id=timetable.id).first()
    if not requirement:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Requirement not found.")
    db.delete(requirement)
    db.commit()


# --- Auto-generation ------------------------------------------------------


def _assign_rooms(db: Session, school_id: uuid.UUID, result: GenerationResult) -> dict[str, uuid.UUID | None]:
    """First-fit greedy room assignment per slot -- rooms are deliberately
    kept out of the CP-SAT model itself (see timetable_generation.py's
    docstring). A lesson with no room left free in its slot is still
    scheduled, just without a room.
    """
    rooms = [r.id for r in db.query(Room).filter_by(school_id=school_id).order_by(Room.name).all()]
    room_by_lesson: dict[str, uuid.UUID | None] = {}
    used_by_slot: dict[str, set[uuid.UUID]] = defaultdict(set)

    for lesson in result.lessons:
        key = f"{lesson.requirement_id}:{lesson.time_slot_id}"
        assigned = None
        for room_id in rooms:
            if room_id not in used_by_slot[lesson.time_slot_id]:
                assigned = room_id
                used_by_slot[lesson.time_slot_id].add(room_id)
                break
        room_by_lesson[key] = assigned

    return room_by_lesson


def generate_timetable(
    db: Session, actor: User, school_id: uuid.UUID, timetable_id: uuid.UUID
) -> tuple[list[TimetableEntry], list[ClassSubjectRequirement], GenerationResult]:
    """Clears every entry on this timetable and replaces it with a freshly
    solved schedule -- see app/planning/timetable_generation.py. Returns
    the new entries alongside the requirements and raw solver result so
    the caller can report requested-vs-scheduled periods per requirement.
    """
    _assert_admin(db, actor, school_id)
    timetable = get_timetable(db, actor, school_id, timetable_id)

    requirements = db.query(ClassSubjectRequirement).filter_by(timetable_id=timetable.id).all()
    if not requirements:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Add at least one class/subject requirement before generating a timetable.")

    slots = db.query(TimeSlot).filter_by(school_id=school_id).all()
    if not slots:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Add time slots before generating a timetable.")

    qualifications = db.query(TeacherSubjectQualification).filter_by(school_id=school_id).all()
    qualified_teachers_by_subject: dict[str, list[str]] = defaultdict(list)
    for q in qualifications:
        qualified_teachers_by_subject[str(q.subject_id)].append(str(q.teacher_user_id))

    unavailability = db.query(TeacherAvailability).filter_by(school_id=school_id, status=AvailabilityStatus.UNAVAILABLE).all()
    unavailable_slot_ids_by_teacher: dict[str, set[str]] = defaultdict(set)
    for a in unavailability:
        unavailable_slot_ids_by_teacher[str(a.teacher_user_id)].add(str(a.time_slot_id))

    result = generate_timetable_pure(requirements, slots, qualified_teachers_by_subject, unavailable_slot_ids_by_teacher)

    room_by_lesson = _assign_rooms(db, school_id, result)

    db.query(TimetableEntry).filter_by(timetable_id=timetable.id).delete()
    db.flush()

    new_entries: list[TimetableEntry] = []
    for lesson in result.lessons:
        room_id = room_by_lesson.get(f"{lesson.requirement_id}:{lesson.time_slot_id}")
        entry = TimetableEntry(
            timetable_id=timetable.id,
            time_slot_id=uuid.UUID(lesson.time_slot_id),
            teacher_user_id=uuid.UUID(lesson.teacher_user_id),
            subject_id=uuid.UUID(lesson.subject_id),
            class_id=uuid.UUID(lesson.class_id),
            room_id=room_id,
        )
        db.add(entry)
        new_entries.append(entry)

    audit_service.log(
        db, actor, school_id, "timetable.generate", {"timetable_id": str(timetable_id), "lessons_scheduled": len(result.lessons)}
    )
    db.commit()
    for entry in new_entries:
        db.refresh(entry)

    return new_entries, requirements, result


def generate_timetable_pure(
    requirements: list[ClassSubjectRequirement],
    slots: list[TimeSlot],
    qualified_teachers_by_subject: dict[str, list[str]],
    unavailable_slot_ids_by_teacher: dict[str, set[str]],
) -> GenerationResult:
    reqs = [Requirement(id=str(r.id), class_id=str(r.class_id), subject_id=str(r.subject_id), periods_per_week=r.periods_per_week) for r in requirements]
    tt_slots = [TimetableSlot(id=str(s.id), day_of_week=s.day_of_week) for s in slots]
    return solve_timetable(reqs, tt_slots, qualified_teachers_by_subject, unavailable_slot_ids_by_teacher)
