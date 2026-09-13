from app.planning.safeguarding import scan_for_safeguarding_concerns
from tests.test_lesson_plans import SAMPLE_CONTENT


def test_clean_content_is_not_flagged():
    flagged, notes = scan_for_safeguarding_concerns(SAMPLE_CONTENT)
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
