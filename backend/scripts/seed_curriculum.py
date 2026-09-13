"""Seed the England / English National Curriculum hierarchy from the
bundled `app/curriculum_packs/` weekly-lesson JSON.

Those files were written for the old lesson-planner phase and are full
weekly lesson content, not a curriculum taxonomy -- this script extracts
the taxonomy that's implicit in them (subject/area codes, objective refs,
weekly themes) and turns it into Curriculum -> KeyStage -> YearGroup ->
Subject -> ProgrammeOfStudy -> CurriculumTopic -> Objective rows. It does
not seed lesson plans themselves; that's a different, later feature.

Idempotent: safe to re-run. Each level is get-or-created by its natural
key rather than inserted unconditionally.

Usage: python -m scripts.seed_curriculum
"""

import glob
import json

from app.db.session import SessionLocal
from app.models.curriculum import Curriculum, CurriculumTopic, KeyStage, Objective, ProgrammeOfStudy, Subject, YearGroup

CURRICULUM_PACKS_DIR = "app/curriculum_packs"

# stage_id (from the pack files) -> (key stage code/name/sort_order, year group code/name/sort_order)
STAGE_META = {
    "eyfs": (("EYFS", "Early Years Foundation Stage", 0), ("RECEPTION", "Reception", 0)),
    "ks1_y1": (("KS1", "Key Stage 1", 1), ("Y1", "Year 1", 0)),
    "ks1_y2": (("KS1", "Key Stage 1", 1), ("Y2", "Year 2", 1)),
}

SUBJECT_NAMES = {
    "ENG": "English",
    "MATHS": "Mathematics",
    "SCI": "Science",
    "ART": "Art & Design",
    "GEOG": "Geography",
    "HIST": "History",
    "CL": "Communication and Language",
    "EAD": "Expressive Arts and Design",
    "LIT": "Literacy",
    "PD": "Physical Development",
    "PSED": "Personal, Social and Emotional Development",
    "UTW": "Understanding the World",
}


def get_or_create(db, model, defaults=None, **kwargs):
    instance = db.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    instance = model(**kwargs, **(defaults or {}))
    db.add(instance)
    db.flush()
    return instance, True


def run() -> None:
    db = SessionLocal()
    stats = {"key_stages": 0, "year_groups": 0, "subjects": 0, "programmes": 0, "topics": 0, "objectives": 0}
    try:
        curriculum, _ = get_or_create(
            db, Curriculum, code="ENC", defaults={"name": "English National Curriculum", "country": "England"}
        )

        key_stage_cache: dict[str, KeyStage] = {}
        year_group_cache: dict[str, YearGroup] = {}
        subject_cache: dict[str, Subject] = {}
        pos_cache: dict[tuple, ProgrammeOfStudy] = {}

        for path in sorted(glob.glob(f"{CURRICULUM_PACKS_DIR}/**/*.json", recursive=True)):
            with open(path) as f:
                data = json.load(f)

            stage_id = data.get("stage_id")
            lessons = data.get("lessons")
            if stage_id not in STAGE_META or not lessons:
                continue  # term/year-map metadata files carry no stage_id/lessons -- not seeded here

            (ks_code, ks_name, ks_sort), (yg_code, yg_name, yg_sort) = STAGE_META[stage_id]

            key_stage = key_stage_cache.get(ks_code)
            if key_stage is None:
                key_stage, created = get_or_create(
                    db, KeyStage, curriculum_id=curriculum.id, code=ks_code, defaults={"name": ks_name, "sort_order": ks_sort}
                )
                key_stage_cache[ks_code] = key_stage
                stats["key_stages"] += created

            year_group = year_group_cache.get(f"{ks_code}:{yg_code}")
            if year_group is None:
                year_group, created = get_or_create(
                    db, YearGroup, key_stage_id=key_stage.id, code=yg_code, defaults={"name": yg_name, "sort_order": yg_sort}
                )
                year_group_cache[f"{ks_code}:{yg_code}"] = year_group
                stats["year_groups"] += created

            week_number = data.get("week_number", 0)
            sub_theme = data.get("sub_theme", f"Week {week_number}")
            topic_by_subject: dict[str, CurriculumTopic] = {}

            for lesson in lessons:
                subject_code = lesson.get("subject_id") or lesson.get("area_id")
                objective_code = lesson.get("objective_ref") or lesson.get("elg_ref")
                description = lesson.get("learning_objective")
                if not subject_code or not objective_code or not description:
                    continue

                subject = subject_cache.get(subject_code)
                if subject is None:
                    subject, created = get_or_create(
                        db,
                        Subject,
                        curriculum_id=curriculum.id,
                        code=subject_code,
                        defaults={"name": SUBJECT_NAMES.get(subject_code, subject_code)},
                    )
                    subject_cache[subject_code] = subject
                    stats["subjects"] += created

                pos_key = (subject.id, year_group.id)
                pos = pos_cache.get(pos_key)
                if pos is None:
                    pos, created = get_or_create(db, ProgrammeOfStudy, subject_id=subject.id, year_group_id=year_group.id)
                    pos_cache[pos_key] = pos
                    stats["programmes"] += created

                topic = topic_by_subject.get(subject_code)
                if topic is None:
                    topic, created = get_or_create(
                        db,
                        CurriculumTopic,
                        programme_of_study_id=pos.id,
                        title=sub_theme,
                        defaults={"sort_order": week_number},
                    )
                    topic_by_subject[subject_code] = topic
                    stats["topics"] += created

                _, created = get_or_create(
                    db, Objective, curriculum_topic_id=topic.id, code=objective_code, description=description
                )
                stats["objectives"] += created

        db.commit()
        print("Curriculum seed complete:", stats)
    finally:
        db.close()


if __name__ == "__main__":
    run()
