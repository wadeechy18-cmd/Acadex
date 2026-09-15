import io

from pydantic import BaseModel

from app.ai.provider import AIGenerationResult, AIProvider, get_ai_provider
from app.main import app
from app.models.curriculum import Curriculum, CurriculumTopic, KeyStage, Objective, ProgrammeOfStudy, Subject, YearGroup
from app.schemas.lesson_plan_content import Differentiation, HomeworkContent, LessonPlanContent, TimelineEntry, TranslatedContent, WorksheetContent
from app.schemas.quick_lesson import QuickLessonIntent
from tests.conftest import auth_headers, register_school, register_teacher

SAMPLE_CONTENT = LessonPlanContent(
    title="Fractions: Halves and Quarters",
    overview="An introduction to halves and quarters using concrete objects.",
    learning_objectives=["Understand what a half is.", "Understand what a quarter is."],
    success_criteria=["I can split a shape into two equal halves."],
    key_vocabulary=["half", "quarter", "equal"],
    prior_knowledge="Children can count to 20 and recognise basic shapes.",
    resources_needed=["Paper circles", "scissors"],
    starter="Discuss sharing a biscuit fairly between two people.",
    teacher_explanation="Model folding a circle into two equal halves.",
    guided_practice="Children fold shapes together with the teacher.",
    independent_practice="Children independently fold and label halves and quarters.",
    key_questions=["What does 'equal' mean?", "How many quarters make a whole?"],
    differentiation=Differentiation(
        support="Fold pre-marked shapes.", core="Fold shapes independently.", greater_depth="Compare halves and quarters of different shapes."
    ),
    assessment="Observe accuracy of folding and correct vocabulary use.",
    misconceptions=["Believing unequal parts can still be called halves."],
    plenary="Share examples of halves and quarters found in the classroom.",
    homework="Find three things at home that can be split into halves.",
    cross_curricular_links="Links to art through symmetry.",
    timeline=[
        TimelineEntry(start_minute=0, end_minute=5, activity="Starter", description="Sharing discussion."),
        TimelineEntry(start_minute=5, end_minute=15, activity="Teacher explanation", description="Model folding."),
        TimelineEntry(start_minute=15, end_minute=25, activity="Guided practice", description="Fold together."),
        TimelineEntry(start_minute=25, end_minute=30, activity="Plenary", description="Share findings."),
    ],
)


SAMPLE_WORKSHEET = WorksheetContent(
    title="Fractions Worksheet",
    instructions="Answer all questions in your book.",
    recall_questions=["What is a half?"],
    understanding_questions=["Explain what makes two parts equal."],
    application_questions=["Split 8 sweets into quarters."],
    challenge_questions=["Compare 1/2 and 3/4."],
)

SAMPLE_HOMEWORK = HomeworkContent(
    title="Fractions Homework",
    instructions="Complete at home with an adult.",
    tasks=["Find three things at home that can be split into halves."],
    estimated_minutes=15,
)

SAMPLE_INTENT = QuickLessonIntent(subject_name="Maths", year_group_or_key_stage="Year 2", topic="Fractions")

SAMPLE_TRANSLATION = TranslatedContent(lesson=SAMPLE_CONTENT, worksheet=SAMPLE_WORKSHEET, homework=SAMPLE_HOMEWORK)


class FakeAIProvider(AIProvider):
    def __init__(self, results: list):
        self._results = list(results)
        self.calls: list[tuple[str, str, type[BaseModel]]] = []

    def generate_structured(self, *, system: str, prompt: str, schema: type[BaseModel]) -> AIGenerationResult:
        self.calls.append((system, prompt, schema))

        _DEFAULTS: dict[type, BaseModel] = {
            LessonPlanContent: SAMPLE_CONTENT,
            WorksheetContent: SAMPLE_WORKSHEET,
            HomeworkContent: SAMPLE_HOMEWORK,
            QuickLessonIntent: SAMPLE_INTENT,
            TranslatedContent: SAMPLE_TRANSLATION,
        }
        matched_default = next((default for schema_type, default in _DEFAULTS.items() if issubclass(schema, schema_type)), None)

        if matched_default is not None:
            raw = self._results.pop(0) if self._results else matched_default
            parsed = raw if isinstance(raw, schema) else schema.model_validate(raw)
        else:
            # A section-regeneration schema has exactly one field -- wrap the
            # queued raw value (e.g. a plain string) as that field's value,
            # defaulting to the matching section of SAMPLE_CONTENT.
            field_name = next(iter(schema.model_fields))
            raw = self._results.pop(0) if self._results else SAMPLE_CONTENT.model_dump()[field_name]
            parsed = schema(**{field_name: raw})

        return AIGenerationResult(parsed=parsed, input_tokens=123, output_tokens=456, model="fake-model")


def override_ai_provider(*results) -> FakeAIProvider:
    fake = FakeAIProvider(list(results))

    def override():
        return fake

    app.dependency_overrides[get_ai_provider] = override
    return fake


def clear_ai_override():
    app.dependency_overrides.pop(get_ai_provider, None)


def _seed_curriculum(db_session):
    curriculum = Curriculum(code="ENC", name="English National Curriculum", country="England")
    db_session.add(curriculum)
    db_session.flush()
    key_stage = KeyStage(curriculum_id=curriculum.id, code="KS1", name="Key Stage 1", sort_order=1)
    db_session.add(key_stage)
    db_session.flush()
    year_group = YearGroup(key_stage_id=key_stage.id, code="Y2", name="Year 2", sort_order=1)
    db_session.add(year_group)
    db_session.flush()
    maths = Subject(curriculum_id=curriculum.id, code="MATHS", name="Mathematics")
    db_session.add(maths)
    db_session.flush()
    pos = ProgrammeOfStudy(subject_id=maths.id, year_group_id=year_group.id)
    db_session.add(pos)
    db_session.flush()
    topic = CurriculumTopic(programme_of_study_id=pos.id, title="Fractions", sort_order=1)
    db_session.add(topic)
    db_session.flush()
    objective = Objective(curriculum_topic_id=topic.id, code="MATHS.FR1", description="Recognise simple fractions.")
    db_session.add(objective)
    db_session.commit()
    return {"subject": maths, "year_group": year_group, "topic": topic}


def _generate_payload(seed, **overrides):
    payload = {
        "subject_id": str(seed["subject"].id),
        "year_group_id": str(seed["year_group"].id),
        "curriculum_topic_id": str(seed["topic"].id),
        "duration_minutes": 30,
        "ability_level": "mixed",
    }
    payload.update(overrides)
    return payload


def test_generate_without_ai_configured_returns_503(client, db_session):
    clear_ai_override()
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    res = client.post("/api/v1/lesson-plans/generate", json=_generate_payload(seed), headers=auth_headers(teacher))
    assert res.status_code == 503


def test_generate_creates_plan_with_normalized_timeline(client, db_session):
    seed = _seed_curriculum(db_session)
    override_ai_provider(SAMPLE_CONTENT)
    teacher = register_teacher(client)

    res = client.post("/api/v1/lesson-plans/generate", json=_generate_payload(seed), headers=auth_headers(teacher))
    clear_ai_override()
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["topic_title"] == "Fractions"
    version = body["current_version"]
    assert version["version_number"] == 1
    assert version["generation_kind"] == "full_generation"
    timeline = version["content"]["timeline"]
    assert timeline[0]["start_minute"] == 0
    assert timeline[-1]["end_minute"] == 30


def test_generate_normalizes_a_timeline_that_does_not_match_duration(client, db_session):
    seed = _seed_curriculum(db_session)
    bad_content = SAMPLE_CONTENT.model_copy(deep=True)
    bad_content.timeline = [TimelineEntry(start_minute=0, end_minute=60, activity="Whole lesson", description="x")]
    override_ai_provider(bad_content)
    teacher = register_teacher(client)

    res = client.post("/api/v1/lesson-plans/generate", json=_generate_payload(seed, duration_minutes=30), headers=auth_headers(teacher))
    clear_ai_override()
    assert res.status_code == 201
    timeline = res.json()["current_version"]["content"]["timeline"]
    assert timeline[-1]["end_minute"] == 30


def test_generate_flags_content_with_safeguarding_concerns(client, db_session):
    seed = _seed_curriculum(db_session)
    flagged_content = SAMPLE_CONTENT.model_copy(deep=True)
    flagged_content.overview = "This lesson explains how to make a weapon safely."
    override_ai_provider(flagged_content)
    teacher = register_teacher(client)

    res = client.post("/api/v1/lesson-plans/generate", json=_generate_payload(seed), headers=auth_headers(teacher))
    clear_ai_override()
    assert res.status_code == 201
    version = res.json()["current_version"]
    assert version["safeguarding_flagged"] is True
    assert "professional judgement" in version["safeguarding_notes"]


def _create_plan(client, seed, teacher):
    override_ai_provider(SAMPLE_CONTENT)
    res = client.post("/api/v1/lesson-plans/generate", json=_generate_payload(seed), headers=auth_headers(teacher))
    clear_ai_override()
    assert res.status_code == 201, res.text
    return res.json()


def test_save_edit_updates_current_version_in_place(client, db_session):
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    plan = _create_plan(client, seed, teacher)
    version_id = plan["current_version"]["id"]

    edited = plan["current_version"]["content"]
    edited["title"] = "Fractions: Edited Title"

    res = client.patch(
        f"/api/v1/lesson-plans/{plan['id']}/versions/{version_id}", json={"content": edited}, headers=auth_headers(teacher)
    )
    assert res.status_code == 200
    assert res.json()["content"]["title"] == "Fractions: Edited Title"
    assert res.json()["version_number"] == 1

    versions = client.get(f"/api/v1/lesson-plans/{plan['id']}/versions", headers=auth_headers(teacher)).json()
    assert len(versions) == 1


def test_save_edit_rejects_editing_a_non_current_version(client, db_session):
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    plan = _create_plan(client, seed, teacher)
    old_version_id = plan["current_version"]["id"]

    client.post(f"/api/v1/lesson-plans/{plan['id']}/versions", json={"content": plan["current_version"]["content"]}, headers=auth_headers(teacher))

    res = client.patch(
        f"/api/v1/lesson-plans/{plan['id']}/versions/{old_version_id}",
        json={"content": plan["current_version"]["content"]},
        headers=auth_headers(teacher),
    )
    assert res.status_code == 400


def test_save_as_new_version_increments_version_number(client, db_session):
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    plan = _create_plan(client, seed, teacher)

    res = client.post(
        f"/api/v1/lesson-plans/{plan['id']}/versions", json={"content": plan["current_version"]["content"]}, headers=auth_headers(teacher)
    )
    assert res.status_code == 201
    assert res.json()["version_number"] == 2
    assert res.json()["generation_kind"] == "manual_edit"


def test_restore_version_creates_a_new_version_copying_old_content(client, db_session):
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    plan = _create_plan(client, seed, teacher)
    v1_id = plan["current_version"]["id"]

    edited = dict(plan["current_version"]["content"])
    edited["title"] = "Changed"
    client.patch(f"/api/v1/lesson-plans/{plan['id']}/versions/{v1_id}", json={"content": edited}, headers=auth_headers(teacher))

    restore = client.post(f"/api/v1/lesson-plans/{plan['id']}/versions/{v1_id}/restore", headers=auth_headers(teacher))
    assert restore.status_code == 201
    assert restore.json()["version_number"] == 2
    assert restore.json()["content"]["title"] == "Changed"  # v1 row itself was edited in place above


def test_regenerate_section_only_changes_that_section(client, db_session):
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    plan = _create_plan(client, seed, teacher)

    override_ai_provider("A brand new starter activity about fractions.")
    res = client.post(
        f"/api/v1/lesson-plans/{plan['id']}/sections/starter/regenerate", json={}, headers=auth_headers(teacher)
    )
    clear_ai_override()
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["version_number"] == 2
    assert body["generation_kind"] == "section_regeneration"
    assert body["content"]["starter"] == "A brand new starter activity about fractions."
    assert body["content"]["title"] == SAMPLE_CONTENT.title  # everything else preserved


def test_regenerate_rejects_an_unknown_section(client, db_session):
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    plan = _create_plan(client, seed, teacher)

    res = client.post(f"/api/v1/lesson-plans/{plan['id']}/sections/title/regenerate", json={}, headers=auth_headers(teacher))
    assert res.status_code == 400


def test_duplicate_plan_creates_a_new_independent_plan(client, db_session):
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    plan = _create_plan(client, seed, teacher)

    res = client.post(f"/api/v1/lesson-plans/{plan['id']}/duplicate", headers=auth_headers(teacher))
    assert res.status_code == 201
    duplicate = res.json()
    assert duplicate["id"] != plan["id"]
    assert duplicate["topic_title"] == "Fractions (copy)"
    assert duplicate["current_version"]["version_number"] == 1


def test_list_get_and_delete_plan(client, db_session):
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    plan = _create_plan(client, seed, teacher)

    listing = client.get("/api/v1/lesson-plans", headers=auth_headers(teacher))
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    get_res = client.get(f"/api/v1/lesson-plans/{plan['id']}", headers=auth_headers(teacher))
    assert get_res.status_code == 200

    delete_res = client.delete(f"/api/v1/lesson-plans/{plan['id']}", headers=auth_headers(teacher))
    assert delete_res.status_code == 204
    assert client.get("/api/v1/lesson-plans", headers=auth_headers(teacher)).json() == []


def test_a_teacher_cannot_see_or_modify_another_teachers_lesson_plan(client, db_session):
    seed = _seed_curriculum(db_session)
    owner = register_teacher(client)
    other = register_teacher(client)
    plan = _create_plan(client, seed, owner)

    other_headers = auth_headers(other)
    assert client.get(f"/api/v1/lesson-plans/{plan['id']}", headers=other_headers).status_code == 404
    assert client.delete(f"/api/v1/lesson-plans/{plan['id']}", headers=other_headers).status_code == 404
    assert client.post(f"/api/v1/lesson-plans/{plan['id']}/duplicate", headers=other_headers).status_code == 404


def test_generation_uses_a_teachers_own_resource_as_context(client, db_session, tmp_path):
    from app.storage.base import LocalStorageBackend, get_storage_backend

    backend = LocalStorageBackend(str(tmp_path), "http://localhost:8000")
    app.dependency_overrides[get_storage_backend] = lambda: backend

    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    upload = client.post(
        "/api/v1/resources",
        files={"file": ("notes.txt", io.BytesIO(b"Use pizza slices to teach fractions."), "text/plain")},
        headers=auth_headers(teacher),
    )
    resource_id = upload.json()["id"]

    fake = override_ai_provider(SAMPLE_CONTENT)
    res = client.post(
        "/api/v1/lesson-plans/generate",
        json=_generate_payload(seed, resource_ids=[resource_id]),
        headers=auth_headers(teacher),
    )
    clear_ai_override()
    app.dependency_overrides.pop(get_storage_backend, None)

    assert res.status_code == 201, res.text
    assert "pizza slices" in fake.calls[0][1]
    assert res.json()["current_version"]["resource_ids"] == [resource_id]


def test_lesson_plan_endpoints_require_authentication(client):
    assert client.get("/api/v1/lesson-plans").status_code == 401


def test_library_can_be_filtered_by_subject_year_group_and_topic(client, db_session):
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    plan = _create_plan(client, seed, teacher)
    headers = auth_headers(teacher)

    matching = client.get(
        "/api/v1/lesson-plans", params={"subject_id": str(seed["subject"].id), "topic": "fraction"}, headers=headers
    )
    assert len(matching.json()) == 1

    no_match = client.get("/api/v1/lesson-plans", params={"topic": "grammar"}, headers=headers)
    assert no_match.json() == []


def test_assigning_a_lesson_plan_to_a_class(client, db_session):
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    headers = auth_headers(teacher)
    plan = _create_plan(client, seed, teacher)

    class_res = client.post("/api/v1/classes", json={"name": "Year 2A"}, headers=headers)
    class_id = class_res.json()["id"]

    assign = client.patch(f"/api/v1/lesson-plans/{plan['id']}/assign", json={"class_id": class_id}, headers=headers)
    assert assign.status_code == 200
    assert assign.json()["class_name"] == "Year 2A"

    filtered = client.get("/api/v1/lesson-plans", params={"class_id": class_id}, headers=headers)
    assert len(filtered.json()) == 1

    unassign = client.patch(f"/api/v1/lesson-plans/{plan['id']}/assign", json={"class_id": None}, headers=headers)
    assert unassign.json()["class_name"] is None


def test_cannot_assign_a_lesson_plan_to_another_teachers_class(client, db_session):
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    other = register_teacher(client)
    plan = _create_plan(client, seed, teacher)

    other_class = client.post("/api/v1/classes", json={"name": "Not yours"}, headers=auth_headers(other))
    res = client.patch(
        f"/api/v1/lesson-plans/{plan['id']}/assign", json={"class_id": other_class.json()["id"]}, headers=auth_headers(teacher)
    )
    assert res.status_code == 404


def test_school_admin_can_browse_lesson_plans_created_within_their_school(client, db_session):
    seed = _seed_curriculum(db_session)
    admin = register_school(client, school_name="Oversight School")
    teacher = register_teacher(client)
    school_id = admin["school"]["id"]
    client.post(f"/api/v1/schools/{school_id}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(admin))

    _create_plan(client, seed, teacher)

    listing = client.get(f"/api/v1/schools/{school_id}/lesson-plans", headers=auth_headers(admin))
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["owner_display_name"] == "Test Teacher"


def test_school_admin_cannot_browse_lesson_plans_from_a_different_school(client, db_session):
    seed = _seed_curriculum(db_session)
    admin_a = register_school(client, school_name="School A Oversight")
    teacher_a = register_teacher(client)
    school_a = admin_a["school"]["id"]
    client.post(f"/api/v1/schools/{school_a}/members", json={"email": teacher_a["email"], "role": "teacher"}, headers=auth_headers(admin_a))
    _create_plan(client, seed, teacher_a)

    admin_b = register_school(client, school_name="School B Oversight")
    res = client.get(f"/api/v1/schools/{school_a}/lesson-plans", headers=auth_headers(admin_b))
    assert res.status_code == 403


def test_school_admin_can_view_a_single_lesson_plan_in_their_school(client, db_session):
    seed = _seed_curriculum(db_session)
    admin = register_school(client, school_name="View School")
    teacher = register_teacher(client)
    school_id = admin["school"]["id"]
    client.post(f"/api/v1/schools/{school_id}/members", json={"email": teacher["email"], "role": "teacher"}, headers=auth_headers(admin))
    plan = _create_plan(client, seed, teacher)

    res = client.get(f"/api/v1/schools/{school_id}/lesson-plans/{plan['id']}", headers=auth_headers(admin))
    assert res.status_code == 200
    assert res.json()["current_version"]["content"]["title"] == SAMPLE_CONTENT.title


def test_school_admin_cannot_view_a_lesson_plan_from_another_school(client, db_session):
    seed = _seed_curriculum(db_session)
    admin_a = register_school(client, school_name="View School A")
    teacher_a = register_teacher(client)
    school_a = admin_a["school"]["id"]
    client.post(f"/api/v1/schools/{school_a}/members", json={"email": teacher_a["email"], "role": "teacher"}, headers=auth_headers(admin_a))
    plan = _create_plan(client, seed, teacher_a)

    admin_b = register_school(client, school_name="View School B")
    res = client.get(f"/api/v1/schools/{admin_b['school']['id']}/lesson-plans/{plan['id']}", headers=auth_headers(admin_b))
    assert res.status_code == 404


def test_a_lesson_plan_created_by_a_teacher_with_no_school_has_no_school_id(client, db_session):
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    plan = _create_plan(client, seed, teacher)
    # No direct field exposed on LessonPlanResponse for school_id today, but
    # a school admin from an unrelated school must still never see it.
    admin = register_school(client, school_name="Unrelated School")
    res = client.get(f"/api/v1/schools/{admin['school']['id']}/lesson-plans", headers=auth_headers(admin))
    assert res.json() == []


def test_generate_produces_a_worksheet_and_homework_alongside_the_lesson(client, db_session):
    seed = _seed_curriculum(db_session)
    override_ai_provider(SAMPLE_CONTENT)
    teacher = register_teacher(client)

    res = client.post("/api/v1/lesson-plans/generate", json=_generate_payload(seed), headers=auth_headers(teacher))
    clear_ai_override()
    assert res.status_code == 201, res.text
    version = res.json()["current_version"]
    assert version["worksheet"]["title"] == SAMPLE_WORKSHEET.title
    assert version["homework_task"]["title"] == SAMPLE_HOMEWORK.title
    assert version["translation_bn"] is None


def test_generate_without_manual_resources_auto_retrieves_from_the_library(client, db_session, tmp_path):
    import io

    from app.storage.base import LocalStorageBackend, get_storage_backend

    backend = LocalStorageBackend(str(tmp_path), "http://localhost:8000")
    app.dependency_overrides[get_storage_backend] = lambda: backend

    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    upload = client.post(
        "/api/v1/resources",
        files={"file": ("notes.txt", io.BytesIO(b"Use pizza slices to teach fractions and halves."), "text/plain")},
        data={"subject_id": str(seed["subject"].id), "year_group_id": str(seed["year_group"].id)},
        headers=auth_headers(teacher),
    )
    assert upload.status_code == 201, upload.text

    fake = override_ai_provider(SAMPLE_CONTENT)
    res = client.post(
        "/api/v1/lesson-plans/generate",
        json=_generate_payload(seed),  # no resource_ids -- must auto-retrieve
        headers=auth_headers(teacher),
    )
    clear_ai_override()
    app.dependency_overrides.pop(get_storage_backend, None)

    assert res.status_code == 201, res.text
    assert "pizza slices" in fake.calls[0][1]
    assert len(res.json()["current_version"]["resource_ids"]) == 1


def test_regenerate_worksheet_only_changes_the_worksheet(client, db_session):
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    plan = _create_plan(client, seed, teacher)

    new_worksheet = SAMPLE_WORKSHEET.model_copy(update={"title": "Brand New Worksheet"})
    override_ai_provider(new_worksheet)
    res = client.post(f"/api/v1/lesson-plans/{plan['id']}/worksheet/regenerate", json={}, headers=auth_headers(teacher))
    clear_ai_override()

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["worksheet"]["title"] == "Brand New Worksheet"
    assert body["homework_task"]["title"] == SAMPLE_HOMEWORK.title
    assert body["content"]["title"] == SAMPLE_CONTENT.title


def test_regenerate_homework_only_changes_the_homework(client, db_session):
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    plan = _create_plan(client, seed, teacher)

    new_homework = SAMPLE_HOMEWORK.model_copy(update={"title": "Brand New Homework"})
    override_ai_provider(new_homework)
    res = client.post(f"/api/v1/lesson-plans/{plan['id']}/homework/regenerate", json={}, headers=auth_headers(teacher))
    clear_ai_override()

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["homework_task"]["title"] == "Brand New Homework"
    assert body["worksheet"]["title"] == SAMPLE_WORKSHEET.title


def test_worksheet_and_homework_export_endpoints(client, db_session):
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    headers = auth_headers(teacher)
    plan = _create_plan(client, seed, teacher)
    version_id = plan["current_version"]["id"]

    pdf = client.get(f"/api/v1/lesson-plans/{plan['id']}/versions/{version_id}/worksheet/export.pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"

    docx = client.get(f"/api/v1/lesson-plans/{plan['id']}/versions/{version_id}/homework/export.docx", headers=headers)
    assert docx.status_code == 200


def test_translate_version_is_cached_across_repeat_requests(client, db_session):
    seed = _seed_curriculum(db_session)
    teacher = register_teacher(client)
    headers = auth_headers(teacher)
    plan = _create_plan(client, seed, teacher)
    version_id = plan["current_version"]["id"]

    fake = override_ai_provider(SAMPLE_TRANSLATION)
    first = client.post(f"/api/v1/lesson-plans/{plan['id']}/versions/{version_id}/translate", headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["translation_bn"]["lesson"]["title"] == SAMPLE_CONTENT.title
    calls_after_first = len(fake.calls)

    second = client.post(f"/api/v1/lesson-plans/{plan['id']}/versions/{version_id}/translate", headers=headers)
    clear_ai_override()
    assert second.status_code == 200
    assert len(fake.calls) == calls_after_first  # cached -- no second AI call
