"""Dev/test-only convenience seed: a demo school with an admin, a few
teachers, classes, a basic timetable, and a task -- enough to click
around the app without registering everything by hand. Never run this
against a production database; it creates known, published credentials.

Usage: python -m scripts.seed_dev_data
"""

import datetime

from app.db.session import SessionLocal
from app.core.security import hash_password
from app.models.class_ import Class
from app.models.curriculum import Subject, YearGroup
from app.models.school import School, SchoolMembership, SchoolMembershipRole
from app.models.task import Task, TaskPriority
from app.models.timetable import AcademicYear, Room, TeacherSubjectQualification, TimeSlot, Timetable, TimetableEntry
from app.models.user import SchoolAdminProfile, TeacherProfile, User, UserRole
from scripts.seed_curriculum import run as seed_curriculum

DEMO_PASSWORD = "DevPassword123"


def get_or_create_user(db, email: str, display_name: str, role: UserRole):
    user = db.query(User).filter_by(email=email).first()
    if user:
        return user
    user = User(email=email, hashed_password=hash_password(DEMO_PASSWORD), role=role)
    db.add(user)
    db.flush()
    if role == UserRole.SCHOOL_ADMIN:
        db.add(SchoolAdminProfile(user_id=user.id, display_name=display_name))
    else:
        db.add(TeacherProfile(user_id=user.id, display_name=display_name))
    return user


def run() -> None:
    seed_curriculum()  # idempotent -- ensures the curriculum browse data exists too

    db = SessionLocal()
    try:
        school = db.query(School).filter_by(name="Demo Primary School").first()
        if school:
            print("Demo data already exists -- skipping.")
            return

        admin = get_or_create_user(db, "admin@demo.acadex.example.com", "Demo Admin", UserRole.SCHOOL_ADMIN)
        teacher_a = get_or_create_user(db, "teacher.a@demo.acadex.example.com", "Alex Teacher", UserRole.TEACHER)
        teacher_b = get_or_create_user(db, "teacher.b@demo.acadex.example.com", "Blake Teacher", UserRole.TEACHER)
        db.flush()

        school = School(name="Demo Primary School", created_by_user_id=admin.id)
        db.add(school)
        db.flush()

        db.add(SchoolMembership(school_id=school.id, user_id=admin.id, role=SchoolMembershipRole.ADMIN))
        db.add(SchoolMembership(school_id=school.id, user_id=teacher_a.id, role=SchoolMembershipRole.TEACHER))
        db.add(SchoolMembership(school_id=school.id, user_id=teacher_b.id, role=SchoolMembershipRole.TEACHER))
        db.flush()

        maths = db.query(Subject).filter_by(code="MATHS").first()
        english = db.query(Subject).filter_by(code="ENG").first()
        year2 = db.query(YearGroup).filter_by(code="Y2").first()

        if maths and year2:
            db.add(TeacherSubjectQualification(school_id=school.id, teacher_user_id=teacher_a.id, subject_id=maths.id))
        if english and year2:
            db.add(TeacherSubjectQualification(school_id=school.id, teacher_user_id=teacher_b.id, subject_id=english.id))

        class_a = Class(owner_user_id=teacher_a.id, name="Year 2A", subject_id=maths.id if maths else None, year_group_id=year2.id if year2 else None)
        db.add(class_a)
        db.flush()

        room = Room(school_id=school.id, name="Room 1", capacity=30)
        db.add(room)
        db.flush()

        academic_year = AcademicYear(
            school_id=school.id, name="2025/2026", start_date=datetime.date(2025, 9, 1), end_date=datetime.date(2026, 7, 31)
        )
        db.add(academic_year)
        db.flush()

        slot = TimeSlot(school_id=school.id, day_of_week=0, start_time=datetime.time(9, 0), end_time=datetime.time(9, 45), label="Period 1")
        db.add(slot)
        db.flush()

        timetable = Timetable(school_id=school.id, academic_year_id=academic_year.id, name="Main Timetable")
        db.add(timetable)
        db.flush()

        if maths:
            db.add(
                TimetableEntry(
                    timetable_id=timetable.id, time_slot_id=slot.id, teacher_user_id=teacher_a.id, subject_id=maths.id, class_id=class_a.id, room_id=room.id
                )
            )

        db.add(
            Task(
                school_id=school.id,
                created_by_user_id=admin.id,
                assigned_to_user_id=teacher_b.id,
                title="Prepare parents' evening handouts",
                description="One per pupil in Year 2A.",
                deadline=datetime.date.today() + datetime.timedelta(days=7),
                priority=TaskPriority.MEDIUM,
            )
        )

        db.commit()
        print(f"Seeded demo school. Login as admin@demo.acadex.example.com / {DEMO_PASSWORD}")
        print(f"Teachers: teacher.a@demo.acadex.example.com, teacher.b@demo.acadex.example.com / {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
