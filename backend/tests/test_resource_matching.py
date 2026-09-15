import uuid

from app.core.security import hash_password
from app.models.curriculum import Curriculum, KeyStage, Subject, YearGroup
from app.models.resource import ExtractionStatus, Resource, ResourceKind
from app.models.user import User, UserRole
from app.planning.resource_matching import find_relevant_resources


def _user(db_session) -> uuid.UUID:
    user = User(email=f"{uuid.uuid4().hex}@example.com", hashed_password=hash_password("SuperSecret123"), role=UserRole.TEACHER)
    db_session.add(user)
    db_session.flush()
    return user.id


def _subject_and_year_group(db_session):
    curriculum = Curriculum(code=f"C{uuid.uuid4().hex[:8]}", name="Test Curriculum", country="England")
    db_session.add(curriculum)
    db_session.flush()
    key_stage = KeyStage(curriculum_id=curriculum.id, code="KS1", name="Key Stage 1", sort_order=1)
    db_session.add(key_stage)
    db_session.flush()
    year_group = YearGroup(key_stage_id=key_stage.id, code="Y2", name="Year 2", sort_order=1)
    subject = Subject(curriculum_id=curriculum.id, code="SCI", name="Science")
    db_session.add_all([year_group, subject])
    db_session.flush()
    return subject, year_group


def _resource(db_session, owner_id, *, name, text=None, subject_id=None, year_group_id=None):
    resource = Resource(
        owner_user_id=owner_id,
        display_name=name,
        original_filename=f"{name}.txt",
        storage_key=f"resources/{owner_id}/{name}.txt",
        content_type="text/plain",
        kind=ResourceKind.TEXT,
        file_size_bytes=100,
        extraction_status=ExtractionStatus.DONE if text else ExtractionStatus.NOT_APPLICABLE,
        extracted_text=text,
        subject_id=subject_id,
        year_group_id=year_group_id,
    )
    db_session.add(resource)
    db_session.flush()
    return resource


def test_tagged_resource_matching_subject_and_year_group_outranks_untagged(db_session):
    owner_id = _user(db_session)
    subject, year_group = _subject_and_year_group(db_session)

    tagged = _resource(
        db_session, owner_id, name="Separating mixtures worksheet", subject_id=subject.id, year_group_id=year_group.id
    )
    untagged = _resource(db_session, owner_id, name="Random maths sheet")
    db_session.commit()

    results = find_relevant_resources(
        db_session, owner_id, subject_id=subject.id, year_group_id=year_group.id, topic_title="separating mixtures"
    )
    assert results[0].id == tagged.id
    assert untagged.id not in [r.id for r in results]


def test_text_overlap_matches_untagged_resources(db_session):
    owner_id = _user(db_session)
    relevant = _resource(db_session, owner_id, name="Notes", text="Use pizza slices to teach fractions and halves and quarters.")
    irrelevant = _resource(db_session, owner_id, name="Other notes", text="A story about a dragon and a castle.")
    db_session.commit()

    results = find_relevant_resources(db_session, owner_id, subject_id=None, year_group_id=None, topic_title="fractions halves quarters")
    result_ids = [r.id for r in results]
    assert relevant.id in result_ids
    assert irrelevant.id not in result_ids


def test_no_matching_resources_returns_empty_list(db_session):
    owner_id = _user(db_session)
    _resource(db_session, owner_id, name="Unrelated", text="A story about a dragon and a castle.")
    db_session.commit()

    results = find_relevant_resources(db_session, owner_id, subject_id=None, year_group_id=None, topic_title="separating mixtures")
    assert results == []


def test_only_searches_the_given_owners_resources(db_session):
    owner_id = _user(db_session)
    other_owner_id = _user(db_session)
    subject, _year_group = _subject_and_year_group(db_session)
    _resource(db_session, other_owner_id, name="Someone else's resource", subject_id=subject.id)
    db_session.commit()

    results = find_relevant_resources(db_session, owner_id, subject_id=subject.id, year_group_id=None, topic_title="anything")
    assert results == []
