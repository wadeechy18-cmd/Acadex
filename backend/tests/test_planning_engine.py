from app.models.lesson_plan import LessonPlanTemplateType
from app.planning.templates import build_sections_from_template
from app.planning.timing import check_timing
from app.planning.validator import validate_lesson_plan
from app.schemas.lesson_plan import LessonPlanContent, LessonSection


def test_standard_template_sections_sum_to_exact_duration():
    for duration in (50, 45, 100, 33, 17):
        sections = build_sections_from_template(LessonPlanTemplateType.STANDARD, duration)
        assert sum(s.duration_minutes for s in sections) == duration


def test_all_templates_sum_to_exact_duration_for_odd_lengths():
    """The largest-remainder allocator must never drift, even for durations
    that don't divide evenly into a template's weights.
    """
    for template_type in LessonPlanTemplateType:
        for duration in (37, 53, 61):
            sections = build_sections_from_template(template_type, duration)
            assert sum(s.duration_minutes for s in sections) == duration, template_type


def test_timing_check_matches_brief_worked_example():
    sections = [
        LessonSection(id="1", type="starter", title="Starter", duration_minutes=5, body=[]),
        LessonSection(id="2", type="retrieval", title="Retrieval", duration_minutes=5, body=[]),
        LessonSection(id="3", type="teacher_input", title="Teacher Input", duration_minutes=10, body=[]),
        LessonSection(id="4", type="practice", title="Practice", duration_minutes=15, body=[]),
        LessonSection(id="5", type="assessment", title="Assessment", duration_minutes=5, body=[]),
        LessonSection(id="6", type="plenary", title="Plenary", duration_minutes=5, body=[]),
    ]
    check = check_timing(sections, planned_minutes=50)
    assert check.total_minutes == 45
    assert check.difference_minutes == 5
    assert check.status == "under"

    labels = {s.label for s in check.suggestions}
    assert "Extend Practice" in labels
    assert "Extend Assessment" in labels
    assert "Extend Plenary" in labels
    assert "Add Practice" in labels


def test_timing_check_ok_when_sections_match_duration():
    sections = [LessonSection(id="1", type="starter", title="Starter", duration_minutes=50, body=[])]
    check = check_timing(sections, planned_minutes=50)
    assert check.status == "ok"
    assert check.suggestions == []


def test_timing_check_over_time_suggests_shortening_longest_section():
    sections = [
        LessonSection(id="1", type="starter", title="Starter", duration_minutes=10, body=[]),
        LessonSection(id="2", type="practice", title="Practice", duration_minutes=50, body=[]),
    ]
    check = check_timing(sections, planned_minutes=50)
    assert check.status == "over"
    assert check.difference_minutes == -10
    assert check.suggestions[0].label == "Shorten Practice"
    assert check.suggestions[0].extend_by_minutes == -10


def test_timing_check_never_suggests_the_same_section_twice():
    """A section whose title/type matches more than one priority keyword
    (e.g. "Practice Assessment" matches both "practice" and "assessment")
    must get exactly one suggestion, not one per matching keyword -- two
    buttons for the same action would let a teacher double-apply the same
    extension.
    """
    sections = [
        LessonSection(id="1", type="starter", title="Starter", duration_minutes=10, body=[]),
        LessonSection(id="2", type="practice_assessment", title="Practice Assessment", duration_minutes=35, body=[]),
    ]
    check = check_timing(sections, planned_minutes=50)
    assert check.status == "under"

    section_2_suggestions = [s for s in check.suggestions if s.section_id == "2"]
    assert len(section_2_suggestions) == 1


def test_timing_check_with_no_sections_suggests_adding_one():
    check = check_timing([], planned_minutes=30)
    assert check.status == "under"
    assert any(s.action == "add_section" for s in check.suggestions)


def test_validator_flags_missing_objectives_and_empty_sections():
    report = validate_lesson_plan(
        title="Blank lesson",
        topic="Blank",
        duration_minutes=50,
        template_type=LessonPlanTemplateType.STANDARD,
        content=LessonPlanContent(),
    )
    messages = [i.message for i in report.issues]
    assert any("learning objectives" in m for m in messages)
    assert any("no sections" in m for m in messages)


def test_validator_requires_assessment_section_for_assessment_template():
    content = LessonPlanContent(
        sections=[LessonSection(id="1", type="starter", title="Starter", duration_minutes=50, body=[])]
    )
    report = validate_lesson_plan(
        title="End of unit test",
        topic="End of unit test",
        duration_minutes=50,
        template_type=LessonPlanTemplateType.ASSESSMENT,
        content=content,
    )
    assert any("assessment section" in i.message for i in report.issues)


def test_validator_flags_safeguarding_sensitive_topic_without_deciding_anything():
    content = LessonPlanContent(learning_objectives=["x"], sections=[
        LessonSection(id="1", type="starter", title="Starter", duration_minutes=50, body=[])
    ])
    report = validate_lesson_plan(
        title="Understanding grooming and online safety",
        topic="Online safety",
        duration_minutes=50,
        template_type=LessonPlanTemplateType.STANDARD,
        content=content,
    )
    safeguarding_issues = [i for i in report.issues if "DSL procedure" in i.message]
    assert len(safeguarding_issues) == 1
    assert safeguarding_issues[0].severity == "info"


def test_validator_does_not_flag_ordinary_topics():
    content = LessonPlanContent(learning_objectives=["x"], sections=[
        LessonSection(id="1", type="starter", title="Starter", duration_minutes=50, body=[])
    ])
    report = validate_lesson_plan(
        title="Photosynthesis",
        topic="Photosynthesis",
        duration_minutes=50,
        template_type=LessonPlanTemplateType.STANDARD,
        content=content,
    )
    assert not any("DSL procedure" in i.message for i in report.issues)
