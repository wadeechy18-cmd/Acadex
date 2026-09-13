import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.class_ import Class
from app.models.curriculum import Subject
from app.models.timetable import AcademicYear, Room, TeacherAvailability, TeacherSubjectQualification, TimeSlot, Timetable, TimetableEntry
from app.models.user import User
from app.schemas.timetable import (
    AcademicYearCreateRequest,
    AcademicYearResponse,
    AvailabilityResponse,
    AvailabilitySetRequest,
    QualificationCreateRequest,
    QualificationResponse,
    RoomCreateRequest,
    RoomResponse,
    TimeSlotCreateRequest,
    TimeSlotResponse,
    TimetableCreateRequest,
    TimetableEntryResponse,
    TimetableEntryUpsertRequest,
    TimetableResponse,
)
from app.services import auth_service, timetable_service

router = APIRouter(prefix="/schools", tags=["timetable"])


@router.post("/{school_id}/academic-years", response_model=AcademicYearResponse, status_code=status.HTTP_201_CREATED)
def create_academic_year(
    school_id: uuid.UUID, payload: AcademicYearCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> AcademicYear:
    return timetable_service.create_academic_year(db, user, school_id, payload)


@router.get("/{school_id}/academic-years", response_model=list[AcademicYearResponse])
def list_academic_years(school_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[AcademicYear]:
    return timetable_service.list_academic_years(db, user, school_id)


@router.post("/{school_id}/rooms", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(school_id: uuid.UUID, payload: RoomCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Room:
    return timetable_service.create_room(db, user, school_id, payload)


@router.get("/{school_id}/rooms", response_model=list[RoomResponse])
def list_rooms(school_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Room]:
    return timetable_service.list_rooms(db, user, school_id)


@router.delete("/{school_id}/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(school_id: uuid.UUID, room_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    timetable_service.delete_room(db, user, school_id, room_id)


@router.post("/{school_id}/time-slots", response_model=TimeSlotResponse, status_code=status.HTTP_201_CREATED)
def create_time_slot(
    school_id: uuid.UUID, payload: TimeSlotCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> TimeSlot:
    return timetable_service.create_time_slot(db, user, school_id, payload)


@router.get("/{school_id}/time-slots", response_model=list[TimeSlotResponse])
def list_time_slots(school_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[TimeSlot]:
    return timetable_service.list_time_slots(db, user, school_id)


@router.delete("/{school_id}/time-slots/{time_slot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_time_slot(school_id: uuid.UUID, time_slot_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    timetable_service.delete_time_slot(db, user, school_id, time_slot_id)


@router.post("/{school_id}/timetables", response_model=TimetableResponse, status_code=status.HTTP_201_CREATED)
def create_timetable(
    school_id: uuid.UUID, payload: TimetableCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Timetable:
    return timetable_service.create_timetable(db, user, school_id, payload)


@router.get("/{school_id}/timetables", response_model=list[TimetableResponse])
def list_timetables(school_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Timetable]:
    return timetable_service.list_timetables(db, user, school_id)


def _entry_response(db: Session, entry: TimetableEntry) -> TimetableEntryResponse:
    teacher = db.get(User, entry.teacher_user_id)
    subject = db.get(Subject, entry.subject_id)
    class_ = db.get(Class, entry.class_id) if entry.class_id else None
    room = db.get(Room, entry.room_id) if entry.room_id else None
    return TimetableEntryResponse(
        id=entry.id,
        time_slot_id=entry.time_slot_id,
        teacher_user_id=entry.teacher_user_id,
        teacher_name=auth_service.get_display_name(db, teacher),
        subject_id=entry.subject_id,
        subject_name=subject.name,
        class_id=entry.class_id,
        class_name=class_.name if class_ else None,
        room_id=entry.room_id,
        room_name=room.name if room else None,
    )


@router.get("/{school_id}/timetables/{timetable_id}/entries", response_model=list[TimetableEntryResponse])
def list_entries(
    school_id: uuid.UUID, timetable_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[TimetableEntryResponse]:
    timetable = timetable_service.get_timetable(db, user, school_id, timetable_id)
    return [_entry_response(db, e) for e in timetable_service.list_entries(db, timetable)]


@router.post("/{school_id}/timetables/{timetable_id}/entries", response_model=TimetableEntryResponse, status_code=status.HTTP_201_CREATED)
def create_entry(
    school_id: uuid.UUID,
    timetable_id: uuid.UUID,
    payload: TimetableEntryUpsertRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TimetableEntryResponse:
    entry = timetable_service.create_entry(db, user, school_id, timetable_id, payload)
    return _entry_response(db, entry)


@router.patch("/{school_id}/timetables/{timetable_id}/entries/{entry_id}", response_model=TimetableEntryResponse)
def update_entry(
    school_id: uuid.UUID,
    timetable_id: uuid.UUID,
    entry_id: uuid.UUID,
    payload: TimetableEntryUpsertRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TimetableEntryResponse:
    entry = timetable_service.update_entry(db, user, school_id, timetable_id, entry_id, payload)
    return _entry_response(db, entry)


@router.delete("/{school_id}/timetables/{timetable_id}/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    school_id: uuid.UUID, timetable_id: uuid.UUID, entry_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    timetable_service.delete_entry(db, user, school_id, timetable_id, entry_id)


def _qualification_response(db: Session, qualification: TeacherSubjectQualification) -> QualificationResponse:
    subject = db.get(Subject, qualification.subject_id)
    return QualificationResponse(id=qualification.id, subject_id=qualification.subject_id, subject_name=subject.name)


@router.post("/{school_id}/teachers/{teacher_id}/qualifications", response_model=QualificationResponse, status_code=status.HTTP_201_CREATED)
def add_qualification(
    school_id: uuid.UUID,
    teacher_id: uuid.UUID,
    payload: QualificationCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QualificationResponse:
    qualification = timetable_service.add_qualification(db, user, school_id, teacher_id, payload.subject_id)
    return _qualification_response(db, qualification)


@router.get("/{school_id}/teachers/{teacher_id}/qualifications", response_model=list[QualificationResponse])
def list_qualifications(
    school_id: uuid.UUID, teacher_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[QualificationResponse]:
    return [_qualification_response(db, q) for q in timetable_service.list_qualifications(db, user, school_id, teacher_id)]


@router.delete("/{school_id}/qualifications/{qualification_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_qualification(
    school_id: uuid.UUID, qualification_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    timetable_service.remove_qualification(db, user, school_id, qualification_id)


@router.put("/{school_id}/teachers/{teacher_id}/availability", response_model=AvailabilityResponse)
def set_availability(
    school_id: uuid.UUID,
    teacher_id: uuid.UUID,
    payload: AvailabilitySetRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AvailabilityResponse:
    record = timetable_service.set_availability(db, user, school_id, teacher_id, payload.time_slot_id, payload.status)
    return AvailabilityResponse(time_slot_id=record.time_slot_id, status=record.status)


@router.get("/{school_id}/teachers/{teacher_id}/availability", response_model=list[AvailabilityResponse])
def list_availability(
    school_id: uuid.UUID, teacher_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[AvailabilityResponse]:
    records = timetable_service.list_availability(db, user, school_id, teacher_id)
    return [AvailabilityResponse(time_slot_id=r.time_slot_id, status=r.status) for r in records]
