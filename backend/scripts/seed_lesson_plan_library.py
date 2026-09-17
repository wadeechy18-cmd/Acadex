"""Turns the bundled EYFS/KS1 weekly lesson content (app/curriculum_packs/)
into real, ready-made LessonPlan rows every teacher can browse and copy --
not just the curriculum taxonomy scripts.seed_curriculum extracts from the
same files. Never calls AI: this is pre-authored content, mapped once into
Acadex's LessonPlanContent shape.

Every imported plan is owned by a single, dedicated "curriculum library"
account (LIBRARY_OWNER_EMAIL) that can never log in (is_active=False) --
it exists purely to hold shared plans. A teacher who wants one clones it
into their own plans via POST /lesson-plans/library/{id}/duplicate, which
reuses the existing duplicate_plan service function; the library copy
itself is never edited in place.

Idempotent: for each (subject, year group, topic) already represented among
the library's plans, its lessons are skipped -- safe to re-run after adding
new curriculum pack files (e.g. previously-missing weeks) without
duplicating what's already imported.

Usage: python -m scripts.seed_lesson_plan_library
"""

import glob
import json

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.curriculum import CurriculumTopic, ProgrammeOfStudy, Subject, YearGroup
from app.models.lesson_plan import AbilityLevel, GenerationKind, LessonPlan, LessonPlanVersion
from app.models.user import TeacherProfile, User, UserRole
from app.planning.safeguarding import scan_for_safeguarding_concerns
from app.planning.timeline import normalize_timeline
from app.schemas.lesson_plan_content import Differentiation, LessonPlanContent, TimelineEntry
from app.services.lesson_plan_service import LIBRARY_OWNER_EMAIL
from scripts.seed_curriculum import CURRICULUM_PACKS_DIR, STAGE_META
from scripts.seed_curriculum import run as seed_curriculum

LIBRARY_OWNER_DISPLAY_NAME = "Acadex Curriculum Library"

# EYFS lessons are shorter than KS1's; both are realistic UK primary lesson
# lengths, not an arbitrary default.
DURATION_BY_STAGE = {"eyfs": 30, "ks1_y1": 45, "ks1_y2": 45}

def _get_or_create_library_user(db) -> User:
    user = db.query(User).filter_by(email=LIBRARY_OWNER_EMAIL).first()
    if user:
        return user
    # is_active=False -- this account exists only to own shared plans and
    # can never log in or authenticate; the password is unusable by design.
    user = User(
        email=LIBRARY_OWNER_EMAIL,
        hashed_password=hash_password("not-a-real-login-" + LIBRARY_OWNER_EMAIL),
        role=UserRole.TEACHER,
        is_active=False,
    )
    db.add(user)
    db.flush()
    db.add(TeacherProfile(user_id=user.id, display_name=LIBRARY_OWNER_DISPLAY_NAME))
    db.flush()
    return user


def _content_from_lesson(lesson: dict) -> LessonPlanContent:
    # KS1 packs use "main_teaching_input"/"independent_task"/a
    # "greater_depth" differentiation key; EYFS packs describe the whole
    # activity in one "main_activity" field (no separate independent
    # task -- EYFS is play-based, not modelled-then-independent) and call
    # the stretch tier "extension" instead of "greater_depth". Both are
    # mapped onto the same schema rather than left blank where a real
    # equivalent exists.
    differentiation_src = lesson.get("differentiation", {})
    main_activity = lesson.get("main_teaching_input") or lesson.get("main_activity", "")
    independent_task = lesson.get("independent_task") or lesson.get("main_activity", "")
    greater_depth = differentiation_src.get("greater_depth") or differentiation_src.get("extension", "")

    has_distinct_independent_task = bool(lesson.get("independent_task"))
    if has_distinct_independent_task:
        timeline = [
            TimelineEntry(start_minute=0, end_minute=5, activity="Starter", description=lesson.get("starter_activity", "")),
            TimelineEntry(start_minute=5, end_minute=20, activity="Teacher input", description=main_activity),
            TimelineEntry(start_minute=20, end_minute=38, activity="Independent task", description=independent_task),
            TimelineEntry(start_minute=38, end_minute=45, activity="Plenary", description=lesson.get("plenary", "")),
        ]
    else:
        # EYFS-shaped lessons describe one blended activity rather than a
        # separate modelled/independent split -- three timeline entries,
        # not four with a fabricated or duplicated middle row.
        timeline = [
            TimelineEntry(start_minute=0, end_minute=5, activity="Starter", description=lesson.get("starter_activity", "")),
            TimelineEntry(start_minute=5, end_minute=25, activity="Main activity", description=main_activity),
            TimelineEntry(start_minute=25, end_minute=30, activity="Plenary", description=lesson.get("plenary", "")),
        ]

    content = LessonPlanContent(
        title=lesson.get("title", "Untitled lesson"),
        overview=f"{lesson.get('title', '')} — {lesson.get('learning_objective', '')}".strip(" —"),
        learning_objectives=[lesson["learning_objective"]] if lesson.get("learning_objective") else [],
        success_criteria=lesson.get("success_criteria", []),
        key_vocabulary=lesson.get("key_vocabulary", []),
        prior_knowledge="",
        resources_needed=lesson.get("resources_needed", []),
        starter=lesson.get("starter_activity", ""),
        teacher_explanation=main_activity,
        guided_practice=main_activity,
        independent_practice=independent_task,
        key_questions=lesson.get("key_questions", []),
        differentiation=Differentiation(
            support=differentiation_src.get("support", ""),
            core="Complete the activity as set for the whole class.",
            greater_depth=greater_depth,
        ),
        assessment=lesson.get("assessment_notes", ""),
        misconceptions=[],
        plenary=lesson.get("plenary", ""),
        homework=lesson.get("home_link", ""),
        cross_curricular_links="",
        timeline=timeline,
    )
    return content


def run() -> None:
    seed_curriculum()  # idempotent -- guarantees the subject/year-group/topic rows this script looks up already exist

    db = SessionLocal()
    try:
        library_user = _get_or_create_library_user(db)
        already_imported = {
            (subject_id, year_group_id, topic_title)
            for subject_id, year_group_id, topic_title in db.query(
                LessonPlan.subject_id, LessonPlan.year_group_id, LessonPlan.topic_title
            ).filter_by(owner_user_id=library_user.id)
        }

        imported = 0
        for path in sorted(glob.glob(f"{CURRICULUM_PACKS_DIR}/**/*.json", recursive=True)):
            with open(path) as f:
                data = json.load(f)

            stage_id = data.get("stage_id")
            lessons = data.get("lessons")
            if stage_id not in STAGE_META or not lessons:
                continue

            _, (yg_code, _, _) = STAGE_META[stage_id]
            # Look up the year group seed_curriculum already created for this
            # stage rather than re-deriving it. YearGroup.code is only unique
            # per key stage, but "RECEPTION"/"Y1"/"Y2" don't collide across
            # the two key stages this data covers, so a plain code lookup
            # is unambiguous here.
            year_group = db.query(YearGroup).filter_by(code=yg_code).first()
            if year_group is None:
                continue

            sub_theme = data.get("sub_theme", f"Week {data.get('week_number', 0)}")
            duration = DURATION_BY_STAGE.get(stage_id, 45)

            for lesson in lessons:
                subject_code = lesson.get("subject_id") or lesson.get("area_id")
                if not subject_code or not lesson.get("learning_objective"):
                    continue

                subject = db.query(Subject).filter_by(code=subject_code).first()
                if subject is None:
                    continue
                pos = db.query(ProgrammeOfStudy).filter_by(subject_id=subject.id, year_group_id=year_group.id).first()
                if pos is None:
                    continue
                topic = db.query(CurriculumTopic).filter_by(programme_of_study_id=pos.id, title=sub_theme).first()
                topic_title = topic.title if topic else sub_theme
                if (subject.id, year_group.id, topic_title) in already_imported:
                    continue

                content = _content_from_lesson(lesson)
                content.timeline = normalize_timeline(content.timeline, duration)
                flagged, notes = scan_for_safeguarding_concerns(content)

                plan = LessonPlan(
                    owner_user_id=library_user.id,
                    school_id=None,
                    subject_id=subject.id,
                    year_group_id=year_group.id,
                    curriculum_topic_id=topic.id if topic else None,
                    topic_title=topic_title,
                    duration_minutes=duration,
                    ability_level=AbilityLevel.MIXED,
                )
                db.add(plan)
                db.flush()

                version = LessonPlanVersion(
                    lesson_plan_id=plan.id,
                    version_number=1,
                    content=content.model_dump(mode="json"),
                    created_by_user_id=library_user.id,
                    generation_kind=GenerationKind.MANUAL_EDIT,
                    generation_notes="Imported from the England/English National Curriculum weekly lesson library.",
                    safeguarding_flagged=flagged,
                    safeguarding_notes=notes,
                )
                db.add(version)
                imported += 1

        db.commit()
        print(f"Lesson plan library seed complete: {imported} plans imported.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
