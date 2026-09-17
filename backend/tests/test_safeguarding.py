from app.planning.safeguarding import scan_for_safeguarding_concerns
from app.schemas.lesson_plan_content import TeacherScriptSection
from tests.test_lesson_plans import SAMPLE_CONTENT, SAMPLE_HOMEWORK, SAMPLE_WORKSHEET


def test_clean_content_is_not_flagged():
    flagged, notes = scan_for_safeguarding_concerns(SAMPLE_CONTENT)
    assert flagged is False
    assert notes is None


def test_clean_content_with_worksheet_and_homework_is_not_flagged():
    flagged, notes = scan_for_safeguarding_concerns(SAMPLE_CONTENT, SAMPLE_WORKSHEET, SAMPLE_HOMEWORK)
    assert flagged is False
    assert notes is None


def test_content_with_a_flagged_term_is_flagged_with_an_explanatory_note():
    content = SAMPLE_CONTENT.model_copy(deep=True)
    content.homework = "Research how to make a bomb for the science fair."
    flagged, notes = scan_for_safeguarding_concerns(content)
    assert flagged is True
    assert "weapons or violent instructions" in notes
    assert "not a substitute" in notes


def test_flag_never_claims_a_compliance_guarantee():
    content = SAMPLE_CONTENT.model_copy(deep=True)
    content.overview = "how to make drugs at home"
    _, notes = scan_for_safeguarding_concerns(content)
    assert "does not guarantee" in notes


def test_unsafe_practical_activity_terms_are_flagged():
    content = SAMPLE_CONTENT.model_copy(deep=True)
    content.teacher_explanation = "Handle broken glass with bare hands to feel the texture."
    flagged, notes = scan_for_safeguarding_concerns(content)
    assert flagged is True
    assert "unsafe practical activity or equipment" in notes


def test_flagged_note_gives_a_concrete_safer_option_not_just_a_category_name():
    content = SAMPLE_CONTENT.model_copy(deep=True)
    content.teacher_explanation = "Handle broken glass with bare hands to feel the texture."
    _, notes = scan_for_safeguarding_concerns(content)
    assert "safer option" in notes.lower()


def test_offsite_trip_terms_are_flagged():
    content = SAMPLE_CONTENT.model_copy(deep=True)
    content.starter = "Begin with a school trip to the local park."
    flagged, notes = scan_for_safeguarding_concerns(content)
    assert flagged is True
    assert "formal risk assessment or school permission" in notes


def test_online_safety_terms_are_flagged():
    content = SAMPLE_CONTENT.model_copy(deep=True)
    content.independent_practice = "Ask pupils to share your home address in the online forum."
    flagged, notes = scan_for_safeguarding_concerns(content)
    assert flagged is True
    assert "online safety or personal information risk" in notes


def test_a_flagged_term_in_the_worksheet_flags_the_whole_scan():
    worksheet = SAMPLE_WORKSHEET.model_copy(update={"recall_questions": ["Explain how to make a bomb."]})
    flagged, notes = scan_for_safeguarding_concerns(SAMPLE_CONTENT, worksheet, SAMPLE_HOMEWORK)
    assert flagged is True
    assert "weapons or violent instructions" in notes


def test_a_flagged_term_in_a_teacher_script_section_flags_the_whole_scan():
    content = SAMPLE_CONTENT.model_copy(deep=True)
    content.starter_script = TeacherScriptSection(teacher_says="Today we will learn how to make a bomb safely.")
    flagged, notes = scan_for_safeguarding_concerns(content)
    assert flagged is True
    assert "weapons or violent instructions" in notes


def test_clean_teacher_script_sections_are_not_flagged():
    content = SAMPLE_CONTENT.model_copy(deep=True)
    content.starter_script = TeacherScriptSection(
        teacher_says="Good morning everyone. Today we are learning about halves.",
        ask=["What do you think a half is?"],
        expected_answers=["Two equal parts."],
        do="Show a paper circle.",
        students_do="Fold their own circle.",
        check_understanding="Ask a pupil to explain in their own words.",
        watch_out_for="Pupils may think unequal parts are still halves.",
    )
    flagged, _ = scan_for_safeguarding_concerns(content)
    assert flagged is False


def test_a_flagged_term_in_the_homework_flags_the_whole_scan():
    homework = SAMPLE_HOMEWORK.model_copy(update={"tasks": ["Research how to buy drugs online."]})
    flagged, notes = scan_for_safeguarding_concerns(SAMPLE_CONTENT, SAMPLE_WORKSHEET, homework)
    assert flagged is True
    assert "substance misuse instructions" in notes
