"""A deliberately narrow, keyword-based safeguarding check run over every
generated lesson plan. This is a software safeguard, not a substitute for
a school's safeguarding policy or a teacher's professional judgement --
see the note text below, which is shown to the teacher whenever something
is flagged. It only ever flags content for human review; it never blocks
or silently alters generation output, and Acadex never claims the check
guarantees legal or policy compliance.

The term list is intentionally small and high-precision rather than
exhaustive: legitimate curriculum content (history topics touching on
war, PSHE topics about staying safe) can share vocabulary with genuinely
concerning content, and a blunt filter would misfire constantly on real
lessons. Flagging errs toward under- rather than over-triggering because
a flag's only effect is "a human should look at this before using it."
"""

from app.schemas.lesson_plan_content import LessonPlanContent

_FLAGGED_TERMS: dict[str, list[str]] = {
    "self-harm or suicide": ["self-harm", "how to self harm", "suicide method", "ways to end your life"],
    "weapons or violent instructions": ["how to make a weapon", "how to make a bomb", "gun instructions", "how to make a knife"],
    "sexual content": ["explicit sexual", "pornograph", "sexual acts"],
    "extremism or hate": ["terrorist recruitment", "racial slur", "hate speech instructions", "extremist propaganda"],
    "substance misuse instructions": ["how to make drugs", "how to buy drugs", "drug dealing instructions"],
}


def _all_text(content: LessonPlanContent) -> str:
    parts = [
        content.title,
        content.overview,
        content.prior_knowledge,
        content.starter,
        content.teacher_explanation,
        content.guided_practice,
        content.independent_practice,
        content.assessment,
        content.plenary,
        content.homework,
        content.cross_curricular_links,
        content.differentiation.support,
        content.differentiation.core,
        content.differentiation.greater_depth,
        *content.learning_objectives,
        *content.success_criteria,
        *content.key_vocabulary,
        *content.resources_needed,
        *content.key_questions,
        *content.misconceptions,
        *(entry.activity for entry in content.timeline),
        *(entry.description for entry in content.timeline),
    ]
    return " ".join(parts).lower()


def scan_for_safeguarding_concerns(content: LessonPlanContent) -> tuple[bool, str | None]:
    """Returns (flagged, note). `note` is None when nothing was flagged."""
    text = _all_text(content)
    matched_categories = sorted({category for category, terms in _FLAGGED_TERMS.items() if any(term in text for term in terms)})

    if not matched_categories:
        return False, None

    note = (
        "Automated safeguarding check flagged this lesson plan for manual review before use. "
        f"Possible concern area(s): {', '.join(matched_categories)}. "
        "This is a keyword-based software check only, not a substitute for your school's safeguarding "
        "policy or your own professional judgement -- it does not guarantee the content is safe or "
        "unsafe, only that it may be worth a closer look."
    )
    return True, note
