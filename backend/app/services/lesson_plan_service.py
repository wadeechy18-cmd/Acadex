import json
import uuid
from datetime import date

from fastapi import HTTPException, status
from pydantic import create_model
from sqlalchemy.orm import Query, Session

from app.ai.provider import AIProvider
from app.models.class_ import Class
from app.models.curriculum import Curriculum, CurriculumTopic, KeyStage, Objective, ProgrammeOfStudy, Subject, YearGroup
from app.models.lesson_plan import AbilityLevel, GenerationKind, LessonPlan, LessonPlanVersion, LessonPlanVersionResource
from app.models.resource import Resource
from app.models.school import SchoolMembershipRole
from app.models.user import User
from app.planning.date_resolution import resolve_relative_date
from app.planning.entity_matching import match_subject, match_year_group
from app.planning.lesson_generation import (
    HOMEWORK_SYSTEM_PROMPT,
    INTENT_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    WORKSHEET_SYSTEM_PROMPT,
    build_generation_prompt,
    build_homework_prompt,
    build_regeneration_prompt,
    build_resource_excerpts,
    build_worksheet_prompt,
)
from app.planning.resource_matching import find_relevant_resources
from app.planning.safeguarding import scan_for_safeguarding_concerns
from app.planning.timeline import normalize_timeline
from app.planning.translation import translate_content
from app.schemas.lesson_plan import GenerateLessonPlanRequest
from app.schemas.lesson_plan_content import REGENERATABLE_SECTIONS, HomeworkContent, LessonPlanContent, TranslatedContent, WorksheetContent
from app.schemas.quick_lesson import QuickLessonIntent
from app.services import school_service

DEFAULT_QUICK_DURATION_MINUTES = 45

# Owner of every pre-authored lesson plan imported from the bundled
# curriculum packs (scripts/seed_lesson_plan_library.py) -- an inactive
# account (can never log in) that exists only to hold plans every teacher
# can browse and duplicate into their own library. See get_library_plan.
LIBRARY_OWNER_EMAIL = "curriculum-library@acadex.internal"


def _get_subject(db: Session, subject_id: uuid.UUID) -> Subject:
    subject = db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found.")
    return subject


def _get_year_group(db: Session, year_group_id: uuid.UUID) -> YearGroup:
    year_group = db.get(YearGroup, year_group_id)
    if not year_group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Year group not found.")
    return year_group


def _resolve_topic_title(db: Session, payload: GenerateLessonPlanRequest) -> tuple[str, list[str]]:
    if payload.curriculum_topic_id:
        topic = db.get(CurriculumTopic, payload.curriculum_topic_id)
        if not topic:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Curriculum topic not found.")
        objectives = db.query(Objective).filter_by(curriculum_topic_id=topic.id).all()
        return topic.title, [o.description for o in objectives]
    if payload.topic_title:
        return payload.topic_title, []
    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provide either curriculum_topic_id or topic_title.")


def _owned_resources(db: Session, user: User, resource_ids: list[uuid.UUID]) -> list[Resource]:
    if not resource_ids:
        return []
    resources = db.query(Resource).filter(Resource.id.in_(resource_ids), Resource.owner_user_id == user.id).all()
    if len(resources) != len(set(resource_ids)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "One or more resources were not found.")
    return resources


def _attach_resources(db: Session, version: LessonPlanVersion, resources: list[Resource]) -> None:
    for resource in resources:
        db.add(LessonPlanVersionResource(lesson_plan_version_id=version.id, resource_id=resource.id))


def _generate_worksheet_and_homework(
    ai_provider: AIProvider,
    *,
    subject_name: str,
    year_group_name: str,
    topic_title: str,
    content: LessonPlanContent,
    resource_excerpts: list[tuple[str, str]],
) -> tuple[WorksheetContent, HomeworkContent]:
    """Every full generation produces a worksheet and homework alongside
    the lesson -- a teacher never has to separately ask for either. Two
    small, single-purpose AI calls (not one call for everything) so each
    stays independently regeneratable later without re-running the others.
    """
    worksheet_prompt = build_worksheet_prompt(
        subject_name=subject_name,
        year_group_name=year_group_name,
        topic_title=topic_title,
        lesson_overview=content.overview,
        learning_objectives=content.learning_objectives,
        resource_excerpts=resource_excerpts,
    )
    worksheet_result = ai_provider.generate_structured(system=WORKSHEET_SYSTEM_PROMPT, prompt=worksheet_prompt, schema=WorksheetContent)

    homework_prompt = build_homework_prompt(
        subject_name=subject_name,
        year_group_name=year_group_name,
        topic_title=topic_title,
        lesson_overview=content.overview,
        learning_objectives=content.learning_objectives,
        resource_excerpts=resource_excerpts,
    )
    homework_result = ai_provider.generate_structured(system=HOMEWORK_SYSTEM_PROMPT, prompt=homework_prompt, schema=HomeworkContent)

    return worksheet_result.parsed, homework_result.parsed


def _finalize_content(
    raw: LessonPlanContent, worksheet: WorksheetContent, homework_task: HomeworkContent, duration_minutes: int
) -> tuple[LessonPlanContent, bool, str | None]:
    raw.timeline = normalize_timeline(raw.timeline, duration_minutes)
    flagged, notes = scan_for_safeguarding_concerns(raw, worksheet, homework_task)
    return raw, flagged, notes


def _generate_full_lesson(
    db: Session,
    ai_provider: AIProvider,
    user: User,
    *,
    subject: Subject,
    year_group: YearGroup,
    curriculum: Curriculum,
    key_stage: KeyStage,
    curriculum_topic_id: uuid.UUID | None,
    topic_title: str,
    curriculum_objectives: list[str],
    duration_minutes: int,
    ability_level,
    teacher_objectives: str | None,
    instructions: str | None,
    resources: list[Resource],
    scheduled_date: date | None = None,
) -> LessonPlan:
    """Shared core behind both the detailed form (generate_lesson_plan) and
    the natural-language quick-generate flow -- one lesson, one worksheet,
    one homework task, safeguarding-checked, persisted as version 1.
    """
    excerpts = build_resource_excerpts([(r.display_name, r.extracted_text) for r in resources])
    prompt = build_generation_prompt(
        curriculum_name=curriculum.name,
        key_stage_name=key_stage.name,
        year_group_name=year_group.name,
        subject_name=subject.name,
        topic_title=topic_title,
        duration_minutes=duration_minutes,
        ability_level=ability_level.value,
        curriculum_objectives=curriculum_objectives,
        teacher_objectives=teacher_objectives,
        instructions=instructions,
        resource_excerpts=excerpts,
    )

    result = ai_provider.generate_structured(system=SYSTEM_PROMPT, prompt=prompt, schema=LessonPlanContent)
    raw_content = result.parsed
    worksheet, homework_task = _generate_worksheet_and_homework(
        ai_provider,
        subject_name=subject.name,
        year_group_name=year_group.name,
        topic_title=topic_title,
        content=raw_content,
        resource_excerpts=excerpts,
    )
    content, flagged, notes = _finalize_content(raw_content, worksheet, homework_task, duration_minutes)

    membership = school_service.get_membership_for_user(db, user)

    plan = LessonPlan(
        owner_user_id=user.id,
        school_id=membership.school_id if membership else None,
        subject_id=subject.id,
        year_group_id=year_group.id,
        curriculum_topic_id=curriculum_topic_id,
        topic_title=topic_title,
        duration_minutes=duration_minutes,
        ability_level=ability_level,
        scheduled_date=scheduled_date,
    )
    db.add(plan)
    db.flush()

    version = LessonPlanVersion(
        lesson_plan_id=plan.id,
        version_number=1,
        content=content.model_dump(mode="json"),
        worksheet_content=worksheet.model_dump(mode="json"),
        homework_content=homework_task.model_dump(mode="json"),
        created_by_user_id=user.id,
        generation_kind=GenerationKind.FULL_GENERATION,
        safeguarding_flagged=flagged,
        safeguarding_notes=notes,
    )
    db.add(version)
    db.flush()
    _attach_resources(db, version, resources)

    db.commit()
    db.refresh(plan)
    return plan


def generate_lesson_plan(
    db: Session, ai_provider: AIProvider, user: User, payload: GenerateLessonPlanRequest
) -> LessonPlan:
    subject = _get_subject(db, payload.subject_id)
    year_group = _get_year_group(db, payload.year_group_id)
    key_stage = db.get(KeyStage, year_group.key_stage_id)
    curriculum = db.get(Curriculum, key_stage.curriculum_id)
    topic_title, curriculum_objectives = _resolve_topic_title(db, payload)

    if payload.resource_ids:
        resources = _owned_resources(db, user, payload.resource_ids)
    else:
        # Resource-first: a teacher who doesn't hand-pick resources still
        # gets the relevant ones from their own library, not none at all.
        resources = find_relevant_resources(
            db,
            user.id,
            subject_id=subject.id,
            year_group_id=year_group.id,
            topic_title=topic_title,
            extra_keywords=payload.objectives or payload.instructions,
        )

    return _generate_full_lesson(
        db,
        ai_provider,
        user,
        subject=subject,
        year_group=year_group,
        curriculum=curriculum,
        key_stage=key_stage,
        curriculum_topic_id=payload.curriculum_topic_id,
        topic_title=topic_title,
        curriculum_objectives=curriculum_objectives,
        duration_minutes=payload.duration_minutes,
        ability_level=payload.ability_level,
        teacher_objectives=payload.objectives,
        instructions=payload.instructions,
        resources=resources,
    )


def _match_curriculum_topic(
    db: Session, subject_id: uuid.UUID, year_group_id: uuid.UUID, topic_phrase: str
) -> CurriculumTopic | None:
    pos = db.query(ProgrammeOfStudy).filter_by(subject_id=subject_id, year_group_id=year_group_id).first()
    if not pos:
        return None
    target = topic_phrase.strip().lower()
    topics = db.query(CurriculumTopic).filter_by(programme_of_study_id=pos.id).all()
    for topic in topics:
        if topic.title.lower() == target:
            return topic
    for topic in topics:
        if topic.title.lower() in target or target in topic.title.lower():
            return topic
    return None


def quick_generate_from_text(db: Session, ai_provider: AIProvider, user: User, text: str) -> LessonPlan:
    """The "type a sentence" entry point. One small AI call turns free text
    into structured intent (app.schemas.quick_lesson.QuickLessonIntent);
    everything after that -- date, subject, year group, topic and resource
    matching -- is deterministic Python against the teacher's own data.
    Raises a 422 (never a guess) when the subject/year group genuinely
    can't be resolved, pointing the teacher back to the detailed form.
    """
    intent_result = ai_provider.generate_structured(system=INTENT_SYSTEM_PROMPT, prompt=text, schema=QuickLessonIntent)
    intent: QuickLessonIntent = intent_result.parsed

    # A teacher who doesn't name a subject/year group probably means "the
    # one I always teach" -- fall back to their most recent lesson plan.
    last_plan = db.query(LessonPlan).filter_by(owner_user_id=user.id).order_by(LessonPlan.created_at.desc()).first()
    subject: Subject | None = None
    year_group: YearGroup | None = None
    curriculum: Curriculum | None = None

    if last_plan is not None:
        subject = db.get(Subject, last_plan.subject_id)
        year_group = db.get(YearGroup, last_plan.year_group_id)
        if subject:
            curriculum = db.get(Curriculum, subject.curriculum_id)

    if curriculum is None:
        curriculum = db.query(Curriculum).order_by(Curriculum.name).first()
    if curriculum is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No curriculum is set up yet. Use the detailed form.")

    matched_subject = match_subject(db, curriculum.id, intent.subject_name)
    if matched_subject is not None:
        subject = matched_subject
    matched_year_group = match_year_group(db, curriculum.id, intent.year_group_or_key_stage)
    if matched_year_group is not None:
        year_group = matched_year_group

    if subject is None or year_group is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Couldn't tell which subject and year group you mean. Mention them explicitly "
            "(e.g. 'Year 2 science') or use the detailed form.",
        )

    key_stage = db.get(KeyStage, year_group.key_stage_id)
    topic = _match_curriculum_topic(db, subject.id, year_group.id, intent.topic)
    if topic is not None:
        objectives = db.query(Objective).filter_by(curriculum_topic_id=topic.id).all()
        topic_title, curriculum_topic_id, curriculum_objectives = topic.title, topic.id, [o.description for o in objectives]
    else:
        topic_title, curriculum_topic_id, curriculum_objectives = intent.topic, None, []

    duration_minutes = max(5, min(240, intent.duration_minutes or DEFAULT_QUICK_DURATION_MINUTES))

    ability_level = AbilityLevel.MIXED
    if intent.ability_level:
        try:
            ability_level = AbilityLevel(intent.ability_level.strip().lower().replace(" ", "_"))
        except ValueError:
            ability_level = AbilityLevel.MIXED

    scheduled_date = resolve_relative_date(intent.relative_date_phrase, date.today())

    resources = find_relevant_resources(
        db,
        user.id,
        subject_id=subject.id,
        year_group_id=year_group.id,
        topic_title=topic_title,
        extra_keywords=intent.additional_instructions,
    )

    return _generate_full_lesson(
        db,
        ai_provider,
        user,
        subject=subject,
        year_group=year_group,
        curriculum=curriculum,
        key_stage=key_stage,
        curriculum_topic_id=curriculum_topic_id,
        topic_title=topic_title,
        curriculum_objectives=curriculum_objectives,
        duration_minutes=duration_minutes,
        ability_level=ability_level,
        teacher_objectives=None,
        instructions=intent.additional_instructions,
        resources=resources,
        scheduled_date=scheduled_date,
    )


def get_owned_plan(db: Session, user: User, plan_id: uuid.UUID) -> LessonPlan:
    plan = db.query(LessonPlan).filter_by(id=plan_id, owner_user_id=user.id).first()
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson plan not found.")
    return plan


def _apply_filters(
    query: Query,
    *,
    subject_id: uuid.UUID | None,
    year_group_id: uuid.UUID | None,
    topic: str | None,
    date_from: date | None,
    date_to: date | None,
    class_id: uuid.UUID | None,
) -> Query:
    if subject_id:
        query = query.filter(LessonPlan.subject_id == subject_id)
    if year_group_id:
        query = query.filter(LessonPlan.year_group_id == year_group_id)
    if topic:
        query = query.filter(LessonPlan.topic_title.ilike(f"%{topic}%"))
    if date_from:
        query = query.filter(LessonPlan.updated_at >= date_from)
    if date_to:
        query = query.filter(LessonPlan.updated_at <= date_to)
    if class_id:
        query = query.filter(LessonPlan.class_id == class_id)
    return query


def list_plans(
    db: Session,
    user: User,
    *,
    subject_id: uuid.UUID | None = None,
    year_group_id: uuid.UUID | None = None,
    topic: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    class_id: uuid.UUID | None = None,
) -> list[LessonPlan]:
    query = db.query(LessonPlan).filter_by(owner_user_id=user.id)
    query = _apply_filters(
        query, subject_id=subject_id, year_group_id=year_group_id, topic=topic, date_from=date_from, date_to=date_to, class_id=class_id
    )
    return query.order_by(LessonPlan.updated_at.desc()).all()


def _get_library_owner(db: Session) -> User | None:
    return db.query(User).filter_by(email=LIBRARY_OWNER_EMAIL).first()


def list_library_plans(
    db: Session,
    *,
    subject_id: uuid.UUID | None = None,
    year_group_id: uuid.UUID | None = None,
    topic: str | None = None,
    limit: int = 50,
) -> list[LessonPlan]:
    """The shared, pre-authored plans every teacher can browse (never
    edited in place -- see duplicate_library_plan). Returns an empty list,
    not an error, if the library hasn't been seeded on this install.

    Capped at `limit` -- the full library runs into the thousands of rows
    (every EYFS/KS1 lesson for a school year), so an unfiltered browse
    returns a manageable first page rather than the whole thing; narrowing
    by subject/year group/topic is how a teacher gets to a specific plan.
    """
    owner = _get_library_owner(db)
    if owner is None:
        return []
    query = db.query(LessonPlan).filter_by(owner_user_id=owner.id)
    query = _apply_filters(query, subject_id=subject_id, year_group_id=year_group_id, topic=topic, date_from=None, date_to=None, class_id=None)
    return query.order_by(LessonPlan.topic_title).limit(limit).all()


def get_library_plan(db: Session, plan_id: uuid.UUID) -> LessonPlan:
    owner = _get_library_owner(db)
    plan = db.query(LessonPlan).filter_by(id=plan_id).first() if owner else None
    if not plan or plan.owner_user_id != owner.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Library lesson plan not found.")
    return plan


def duplicate_library_plan(db: Session, user: User, plan_id: uuid.UUID) -> LessonPlan:
    """Copies a library plan into the requesting teacher's own plans --
    the teacher's copy is a completely independent LessonPlan they can
    edit, regenerate, and export like any other; the library original is
    never modified.
    """
    library_plan = get_library_plan(db, plan_id)
    return duplicate_plan(db, user, library_plan)


def list_school_plans(
    db: Session,
    actor: User,
    school_id: uuid.UUID,
    *,
    subject_id: uuid.UUID | None = None,
    year_group_id: uuid.UUID | None = None,
    topic: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    class_id: uuid.UUID | None = None,
) -> list[LessonPlan]:
    """Read-only oversight for a school admin -- every lesson plan created
    by a teacher who was a member of this school at generation time, never
    plans from any other school.
    """
    school_service.assert_school_member(db, actor, school_id, min_role=SchoolMembershipRole.ADMIN)
    query = db.query(LessonPlan).filter_by(school_id=school_id)
    query = _apply_filters(
        query, subject_id=subject_id, year_group_id=year_group_id, topic=topic, date_from=date_from, date_to=date_to, class_id=class_id
    )
    return query.order_by(LessonPlan.updated_at.desc()).all()


def get_school_plan(db: Session, actor: User, school_id: uuid.UUID, plan_id: uuid.UUID) -> LessonPlan:
    school_service.assert_school_member(db, actor, school_id, min_role=SchoolMembershipRole.ADMIN)
    plan = db.query(LessonPlan).filter_by(id=plan_id, school_id=school_id).first()
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson plan not found.")
    return plan


def assign_class(db: Session, user: User, plan: LessonPlan, class_id: uuid.UUID | None) -> LessonPlan:
    if class_id is not None:
        class_ = db.query(Class).filter_by(id=class_id, owner_user_id=user.id).first()
        if not class_:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Class not found.")
    plan.class_id = class_id
    db.commit()
    db.refresh(plan)
    return plan


def list_versions(db: Session, plan: LessonPlan) -> list[LessonPlanVersion]:
    return db.query(LessonPlanVersion).filter_by(lesson_plan_id=plan.id).order_by(LessonPlanVersion.version_number.desc()).all()


def get_current_version(db: Session, plan: LessonPlan) -> LessonPlanVersion:
    version = (
        db.query(LessonPlanVersion)
        .filter_by(lesson_plan_id=plan.id)
        .order_by(LessonPlanVersion.version_number.desc())
        .first()
    )
    if not version:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This lesson plan has no versions.")
    return version


def get_version(db: Session, plan: LessonPlan, version_id: uuid.UUID) -> LessonPlanVersion:
    version = db.query(LessonPlanVersion).filter_by(id=version_id, lesson_plan_id=plan.id).first()
    if not version:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Version not found.")
    return version


def resource_ids_for_version(db: Session, version: LessonPlanVersion) -> list[uuid.UUID]:
    links = db.query(LessonPlanVersionResource).filter_by(lesson_plan_version_id=version.id).all()
    return [link.resource_id for link in links]


def _carried_worksheet(source: LessonPlanVersion, override: WorksheetContent | None) -> tuple[WorksheetContent | None, dict | None]:
    if override is not None:
        return override, override.model_dump(mode="json")
    if source.worksheet_content:
        return WorksheetContent.model_validate(source.worksheet_content), source.worksheet_content
    return None, None


def _carried_homework(source: LessonPlanVersion, override: HomeworkContent | None) -> tuple[HomeworkContent | None, dict | None]:
    if override is not None:
        return override, override.model_dump(mode="json")
    if source.homework_content:
        return HomeworkContent.model_validate(source.homework_content), source.homework_content
    return None, None


def save_edit(
    db: Session,
    user: User,
    plan: LessonPlan,
    version_id: uuid.UUID,
    content: LessonPlanContent,
    worksheet: WorksheetContent | None = None,
    homework_task: HomeworkContent | None = None,
) -> LessonPlanVersion:
    version = get_version(db, plan, version_id)
    current = get_current_version(db, plan)
    if version.id != current.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only the current version can be edited in place. Restore it first.")

    content.timeline = normalize_timeline(content.timeline, plan.duration_minutes)
    worksheet_obj, worksheet_dict = _carried_worksheet(version, worksheet)
    homework_obj, homework_dict = _carried_homework(version, homework_task)
    flagged, notes = scan_for_safeguarding_concerns(content, worksheet_obj, homework_obj)
    version.content = content.model_dump(mode="json")
    version.worksheet_content = worksheet_dict
    version.homework_content = homework_dict
    version.safeguarding_flagged = flagged
    version.safeguarding_notes = notes
    db.commit()
    db.refresh(version)
    return version


def save_as_new_version(
    db: Session,
    user: User,
    plan: LessonPlan,
    content: LessonPlanContent,
    worksheet: WorksheetContent | None = None,
    homework_task: HomeworkContent | None = None,
) -> LessonPlanVersion:
    current = get_current_version(db, plan)
    content.timeline = normalize_timeline(content.timeline, plan.duration_minutes)
    worksheet_obj, worksheet_dict = _carried_worksheet(current, worksheet)
    homework_obj, homework_dict = _carried_homework(current, homework_task)
    flagged, notes = scan_for_safeguarding_concerns(content, worksheet_obj, homework_obj)

    version = LessonPlanVersion(
        lesson_plan_id=plan.id,
        version_number=current.version_number + 1,
        content=content.model_dump(mode="json"),
        worksheet_content=worksheet_dict,
        homework_content=homework_dict,
        created_by_user_id=user.id,
        generation_kind=GenerationKind.MANUAL_EDIT,
        safeguarding_flagged=flagged,
        safeguarding_notes=notes,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def regenerate_section(
    db: Session, ai_provider: AIProvider, user: User, plan: LessonPlan, section_name: str, instructions: str | None
) -> LessonPlanVersion:
    if section_name not in REGENERATABLE_SECTIONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{section_name}' is not a regeneratable section.")

    current = get_current_version(db, plan)
    current_content = LessonPlanContent.model_validate(current.content)

    prompt = build_regeneration_prompt(
        section_name=section_name,
        current_content_json=json.dumps(current.content, indent=2),
        extra_instructions=instructions,
    )
    section_schema = create_model(f"Section_{section_name}", **{section_name: (REGENERATABLE_SECTIONS[section_name], ...)})
    result = ai_provider.generate_structured(system=SYSTEM_PROMPT, prompt=prompt, schema=section_schema)
    new_value = getattr(result.parsed, section_name)

    updated_dict = current_content.model_dump()
    updated_dict[section_name] = new_value.model_dump() if hasattr(new_value, "model_dump") else new_value
    updated_content = LessonPlanContent.model_validate(updated_dict)
    updated_content.timeline = normalize_timeline(updated_content.timeline, plan.duration_minutes)
    worksheet_obj, worksheet_dict = _carried_worksheet(current, None)
    homework_obj, homework_dict = _carried_homework(current, None)
    flagged, notes = scan_for_safeguarding_concerns(updated_content, worksheet_obj, homework_obj)

    version = LessonPlanVersion(
        lesson_plan_id=plan.id,
        version_number=current.version_number + 1,
        content=updated_content.model_dump(mode="json"),
        worksheet_content=worksheet_dict,
        homework_content=homework_dict,
        created_by_user_id=user.id,
        generation_kind=GenerationKind.SECTION_REGENERATION,
        generation_notes=f"Regenerated section: {section_name}",
        safeguarding_flagged=flagged,
        safeguarding_notes=notes,
    )
    db.add(version)
    db.flush()
    _attach_resources(db, version, [db.get(Resource, rid) for rid in resource_ids_for_version(db, current)])
    db.commit()
    db.refresh(version)
    return version


def _resource_excerpts_for_version(db: Session, version: LessonPlanVersion) -> tuple[list[Resource], list[tuple[str, str]]]:
    resources = [r for r in (db.get(Resource, rid) for rid in resource_ids_for_version(db, version)) if r is not None]
    excerpts = build_resource_excerpts([(r.display_name, r.extracted_text) for r in resources])
    return resources, excerpts


def regenerate_worksheet(
    db: Session, ai_provider: AIProvider, user: User, plan: LessonPlan, instructions: str | None
) -> LessonPlanVersion:
    current = get_current_version(db, plan)
    content = LessonPlanContent.model_validate(current.content)
    subject = _get_subject(db, plan.subject_id)
    year_group = _get_year_group(db, plan.year_group_id)
    resources, excerpts = _resource_excerpts_for_version(db, current)

    prompt = build_worksheet_prompt(
        subject_name=subject.name,
        year_group_name=year_group.name,
        topic_title=plan.topic_title,
        lesson_overview=content.overview,
        learning_objectives=content.learning_objectives,
        resource_excerpts=excerpts,
    )
    if instructions:
        prompt += f"\nAdditional instruction for this regeneration: {instructions}"

    result = ai_provider.generate_structured(system=WORKSHEET_SYSTEM_PROMPT, prompt=prompt, schema=WorksheetContent)
    worksheet = result.parsed
    homework_obj, homework_dict = _carried_homework(current, None)
    flagged, notes = scan_for_safeguarding_concerns(content, worksheet, homework_obj)

    version = LessonPlanVersion(
        lesson_plan_id=plan.id,
        version_number=current.version_number + 1,
        content=current.content,
        worksheet_content=worksheet.model_dump(mode="json"),
        homework_content=homework_dict,
        created_by_user_id=user.id,
        generation_kind=GenerationKind.SECTION_REGENERATION,
        generation_notes="Regenerated worksheet",
        safeguarding_flagged=flagged,
        safeguarding_notes=notes,
    )
    db.add(version)
    db.flush()
    _attach_resources(db, version, resources)
    db.commit()
    db.refresh(version)
    return version


def regenerate_homework(
    db: Session, ai_provider: AIProvider, user: User, plan: LessonPlan, instructions: str | None
) -> LessonPlanVersion:
    current = get_current_version(db, plan)
    content = LessonPlanContent.model_validate(current.content)
    subject = _get_subject(db, plan.subject_id)
    year_group = _get_year_group(db, plan.year_group_id)
    resources, excerpts = _resource_excerpts_for_version(db, current)

    prompt = build_homework_prompt(
        subject_name=subject.name,
        year_group_name=year_group.name,
        topic_title=plan.topic_title,
        lesson_overview=content.overview,
        learning_objectives=content.learning_objectives,
        resource_excerpts=excerpts,
    )
    if instructions:
        prompt += f"\nAdditional instruction for this regeneration: {instructions}"

    result = ai_provider.generate_structured(system=HOMEWORK_SYSTEM_PROMPT, prompt=prompt, schema=HomeworkContent)
    homework_task = result.parsed
    worksheet_obj, worksheet_dict = _carried_worksheet(current, None)
    flagged, notes = scan_for_safeguarding_concerns(content, worksheet_obj, homework_task)

    version = LessonPlanVersion(
        lesson_plan_id=plan.id,
        version_number=current.version_number + 1,
        content=current.content,
        worksheet_content=worksheet_dict,
        homework_content=homework_task.model_dump(mode="json"),
        created_by_user_id=user.id,
        generation_kind=GenerationKind.SECTION_REGENERATION,
        generation_notes="Regenerated homework",
        safeguarding_flagged=flagged,
        safeguarding_notes=notes,
    )
    db.add(version)
    db.flush()
    _attach_resources(db, version, resources)
    db.commit()
    db.refresh(version)
    return version


def translate_version(
    db: Session, ai_provider: AIProvider, user: User, plan: LessonPlan, version_id: uuid.UUID, force: bool = False
) -> LessonPlanVersion:
    """Cached: a version is only ever translated once unless force=True is
    explicitly requested, so switching the "English / বাংলা" toggle back
    and forth never re-triggers an AI call.
    """
    version = get_version(db, plan, version_id)
    if version.translation_bn and not force:
        return version

    content = LessonPlanContent.model_validate(version.content)
    worksheet = WorksheetContent.model_validate(version.worksheet_content) if version.worksheet_content else None
    homework_task = HomeworkContent.model_validate(version.homework_content) if version.homework_content else None

    translated: TranslatedContent = translate_content(ai_provider, content, worksheet, homework_task)
    version.translation_bn = translated.model_dump(mode="json")
    db.commit()
    db.refresh(version)
    return version


def restore_version(db: Session, user: User, plan: LessonPlan, version_id: uuid.UUID) -> LessonPlanVersion:
    target = get_version(db, plan, version_id)
    current = get_current_version(db, plan)

    version = LessonPlanVersion(
        lesson_plan_id=plan.id,
        version_number=current.version_number + 1,
        content=target.content,
        worksheet_content=target.worksheet_content,
        homework_content=target.homework_content,
        translation_bn=target.translation_bn,
        created_by_user_id=user.id,
        generation_kind=GenerationKind.MANUAL_EDIT,
        generation_notes=f"Restored from version {target.version_number}",
        safeguarding_flagged=target.safeguarding_flagged,
        safeguarding_notes=target.safeguarding_notes,
    )
    db.add(version)
    db.flush()
    _attach_resources(db, version, [db.get(Resource, rid) for rid in resource_ids_for_version(db, target)])
    db.commit()
    db.refresh(version)
    return version


def duplicate_plan(db: Session, user: User, plan: LessonPlan) -> LessonPlan:
    current = get_current_version(db, plan)

    new_plan = LessonPlan(
        owner_user_id=user.id,
        subject_id=plan.subject_id,
        year_group_id=plan.year_group_id,
        curriculum_topic_id=plan.curriculum_topic_id,
        topic_title=f"{plan.topic_title} (copy)",
        duration_minutes=plan.duration_minutes,
        ability_level=plan.ability_level,
    )
    db.add(new_plan)
    db.flush()

    version = LessonPlanVersion(
        lesson_plan_id=new_plan.id,
        version_number=1,
        content=current.content,
        worksheet_content=current.worksheet_content,
        homework_content=current.homework_content,
        translation_bn=current.translation_bn,
        created_by_user_id=user.id,
        generation_kind=GenerationKind.MANUAL_EDIT,
        generation_notes=f"Duplicated from lesson plan {plan.id}",
        safeguarding_flagged=current.safeguarding_flagged,
        safeguarding_notes=current.safeguarding_notes,
    )
    db.add(version)
    db.flush()
    _attach_resources(db, version, [db.get(Resource, rid) for rid in resource_ids_for_version(db, current)])
    db.commit()
    db.refresh(new_plan)
    return new_plan


def delete_plan(db: Session, user: User, plan: LessonPlan) -> None:
    db.delete(plan)
    db.commit()
