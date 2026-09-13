import json
import uuid

from fastapi import HTTPException, status
from pydantic import create_model
from sqlalchemy.orm import Session

from app.ai.provider import AIProvider
from app.models.curriculum import Curriculum, CurriculumTopic, KeyStage, Objective, Subject, YearGroup
from app.models.lesson_plan import GenerationKind, LessonPlan, LessonPlanVersion, LessonPlanVersionResource
from app.models.resource import Resource
from app.models.user import User
from app.planning.lesson_generation import SYSTEM_PROMPT, build_generation_prompt, build_regeneration_prompt, build_resource_excerpts
from app.planning.safeguarding import scan_for_safeguarding_concerns
from app.planning.timeline import normalize_timeline
from app.schemas.lesson_plan import GenerateLessonPlanRequest
from app.schemas.lesson_plan_content import REGENERATABLE_SECTIONS, LessonPlanContent


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


def _finalize_content(raw: LessonPlanContent, duration_minutes: int) -> tuple[LessonPlanContent, bool, str | None]:
    raw.timeline = normalize_timeline(raw.timeline, duration_minutes)
    flagged, notes = scan_for_safeguarding_concerns(raw)
    return raw, flagged, notes


def generate_lesson_plan(
    db: Session, ai_provider: AIProvider, user: User, payload: GenerateLessonPlanRequest
) -> LessonPlan:
    subject = _get_subject(db, payload.subject_id)
    year_group = _get_year_group(db, payload.year_group_id)
    key_stage = db.get(KeyStage, year_group.key_stage_id)
    curriculum = db.get(Curriculum, key_stage.curriculum_id)
    topic_title, curriculum_objectives = _resolve_topic_title(db, payload)
    resources = _owned_resources(db, user, payload.resource_ids)

    excerpts = build_resource_excerpts([(r.display_name, r.extracted_text) for r in resources])
    prompt = build_generation_prompt(
        curriculum_name=curriculum.name,
        key_stage_name=key_stage.name,
        year_group_name=year_group.name,
        subject_name=subject.name,
        topic_title=topic_title,
        duration_minutes=payload.duration_minutes,
        ability_level=payload.ability_level.value,
        curriculum_objectives=curriculum_objectives,
        teacher_objectives=payload.objectives,
        instructions=payload.instructions,
        resource_excerpts=excerpts,
    )

    result = ai_provider.generate_structured(system=SYSTEM_PROMPT, prompt=prompt, schema=LessonPlanContent)
    content, flagged, notes = _finalize_content(result.parsed, payload.duration_minutes)

    plan = LessonPlan(
        owner_user_id=user.id,
        subject_id=subject.id,
        year_group_id=year_group.id,
        curriculum_topic_id=payload.curriculum_topic_id,
        topic_title=topic_title,
        duration_minutes=payload.duration_minutes,
        ability_level=payload.ability_level,
    )
    db.add(plan)
    db.flush()

    version = LessonPlanVersion(
        lesson_plan_id=plan.id,
        version_number=1,
        content=content.model_dump(mode="json"),
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


def get_owned_plan(db: Session, user: User, plan_id: uuid.UUID) -> LessonPlan:
    plan = db.query(LessonPlan).filter_by(id=plan_id, owner_user_id=user.id).first()
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson plan not found.")
    return plan


def list_plans(db: Session, user: User) -> list[LessonPlan]:
    return db.query(LessonPlan).filter_by(owner_user_id=user.id).order_by(LessonPlan.updated_at.desc()).all()


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


def save_edit(db: Session, user: User, plan: LessonPlan, version_id: uuid.UUID, content: LessonPlanContent) -> LessonPlanVersion:
    version = get_version(db, plan, version_id)
    current = get_current_version(db, plan)
    if version.id != current.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only the current version can be edited in place. Restore it first.")

    content.timeline = normalize_timeline(content.timeline, plan.duration_minutes)
    flagged, notes = scan_for_safeguarding_concerns(content)
    version.content = content.model_dump(mode="json")
    version.safeguarding_flagged = flagged
    version.safeguarding_notes = notes
    db.commit()
    db.refresh(version)
    return version


def save_as_new_version(db: Session, user: User, plan: LessonPlan, content: LessonPlanContent) -> LessonPlanVersion:
    current = get_current_version(db, plan)
    content.timeline = normalize_timeline(content.timeline, plan.duration_minutes)
    flagged, notes = scan_for_safeguarding_concerns(content)

    version = LessonPlanVersion(
        lesson_plan_id=plan.id,
        version_number=current.version_number + 1,
        content=content.model_dump(mode="json"),
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
    flagged, notes = scan_for_safeguarding_concerns(updated_content)

    version = LessonPlanVersion(
        lesson_plan_id=plan.id,
        version_number=current.version_number + 1,
        content=updated_content.model_dump(mode="json"),
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


def restore_version(db: Session, user: User, plan: LessonPlan, version_id: uuid.UUID) -> LessonPlanVersion:
    target = get_version(db, plan, version_id)
    current = get_current_version(db, plan)

    version = LessonPlanVersion(
        lesson_plan_id=plan.id,
        version_number=current.version_number + 1,
        content=target.content,
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
