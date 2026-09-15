from app.planning.safeguarding import scan_for_safeguarding_concerns
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


def test_a_flagged_term_in_the_homework_flags_the_whole_scan():
    homework = SAMPLE_HOMEWORK.model_copy(update={"tasks": ["Research how to buy drugs online."]})
    flagged, notes = scan_for_safeguarding_concerns(SAMPLE_CONTENT, SAMPLE_WORKSHEET, homework)
    assert flagged is True
    assert "substance misuse instructions" in notes
