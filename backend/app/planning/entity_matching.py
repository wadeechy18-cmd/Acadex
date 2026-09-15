"""Matching the free-text subject/year-group phrases the AI extracts from a
teacher's request (see app.schemas.quick_lesson.QuickLessonIntent) against
the real Curriculum/Subject/YearGroup rows already in the database. Pure
Python string matching -- deliberately simple and easy to reason about,
never an AI call: a teacher's own curriculum data is a small, known list,
not something that needs fuzzy ML matching.
"""

import re

from sqlalchemy.orm import Session

from app.models.curriculum import KeyStage, Subject, YearGroup

_EYFS_ALIASES = {"early years", "eyfs", "reception", "nursery", "foundation stage"}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def match_subject(db: Session, curriculum_id, phrase: str | None) -> Subject | None:
    if not phrase:
        return None
    target = _normalize(phrase)
    subjects = db.query(Subject).filter_by(curriculum_id=curriculum_id).all()

    for subject in subjects:
        if subject.name.lower() == target or subject.code.lower() == target:
            return subject
    for subject in subjects:
        if subject.name.lower() in target or target in subject.name.lower():
            return subject
    return None


def match_year_group(db: Session, curriculum_id, phrase: str | None) -> YearGroup | None:
    if not phrase:
        return None
    target = _normalize(phrase)
    year_groups = (
        db.query(YearGroup).join(KeyStage, YearGroup.key_stage_id == KeyStage.id).filter(KeyStage.curriculum_id == curriculum_id).all()
    )

    for year_group in year_groups:
        if year_group.name.lower() == target or year_group.code.lower() == target.replace(" ", ""):
            return year_group

    match = re.search(r"year\s*(\d+)|\by(\d+)\b", target)
    if match:
        number = match.group(1) or match.group(2)
        for year_group in year_groups:
            if year_group.code.lower() == f"y{number}" or year_group.name.lower() == f"year {number}":
                return year_group

    if any(alias in target for alias in _EYFS_ALIASES):
        key_stages = {ks.id: ks for ks in db.query(KeyStage).filter_by(curriculum_id=curriculum_id).all()}
        for year_group in year_groups:
            key_stage = key_stages.get(year_group.key_stage_id)
            if "reception" in year_group.name.lower() or (key_stage and "eyfs" in key_stage.code.lower()):
                return year_group

    return None
