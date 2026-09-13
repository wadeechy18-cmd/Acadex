import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.curriculum import Curriculum, CurriculumTopic, KeyStage, Objective, ProgrammeOfStudy, Subject, YearGroup


def list_curricula(db: Session) -> list[Curriculum]:
    return db.query(Curriculum).order_by(Curriculum.name).all()


def list_key_stages(db: Session, curriculum_id: uuid.UUID) -> list[KeyStage]:
    return db.query(KeyStage).filter_by(curriculum_id=curriculum_id).order_by(KeyStage.sort_order).all()


def list_year_groups(db: Session, key_stage_id: uuid.UUID) -> list[YearGroup]:
    return db.query(YearGroup).filter_by(key_stage_id=key_stage_id).order_by(YearGroup.sort_order).all()


def list_subjects_for_year_group(db: Session, year_group_id: uuid.UUID) -> list[Subject]:
    """Only subjects that actually have a programme of study for this year
    group -- e.g. a Reception year group only offers the seven EYFS areas
    of learning, not KS1-only subjects.
    """
    return (
        db.query(Subject)
        .join(ProgrammeOfStudy, ProgrammeOfStudy.subject_id == Subject.id)
        .filter(ProgrammeOfStudy.year_group_id == year_group_id)
        .order_by(Subject.name)
        .all()
    )


def _get_programme_of_study(db: Session, subject_id: uuid.UUID, year_group_id: uuid.UUID) -> ProgrammeOfStudy:
    pos = db.query(ProgrammeOfStudy).filter_by(subject_id=subject_id, year_group_id=year_group_id).first()
    if not pos:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No programme of study for that subject and year group.")
    return pos


def list_topics(db: Session, subject_id: uuid.UUID, year_group_id: uuid.UUID) -> list[CurriculumTopic]:
    pos = _get_programme_of_study(db, subject_id, year_group_id)
    return db.query(CurriculumTopic).filter_by(programme_of_study_id=pos.id).order_by(CurriculumTopic.sort_order).all()


def list_objectives(db: Session, topic_id: uuid.UUID) -> list[Objective]:
    topic = db.get(CurriculumTopic, topic_id)
    if not topic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic not found.")
    return db.query(Objective).filter_by(curriculum_topic_id=topic_id).order_by(Objective.code).all()
