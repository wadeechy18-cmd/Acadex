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

from app.schemas.lesson_plan_content import HomeworkContent, LessonPlanContent, WorksheetContent

_FLAGGED_TERMS: dict[str, list[str]] = {
    "self-harm or suicide": ["self-harm", "how to self harm", "suicide method", "ways to end your life"],
    "weapons or violent instructions": ["how to make a weapon", "how to make a bomb", "gun instructions", "how to make a knife"],
    "sexual content": ["explicit sexual", "pornograph", "sexual acts"],
    "extremism or hate": ["terrorist recruitment", "racial slur", "hate speech instructions", "extremist propaganda"],
    "substance misuse instructions": ["how to make drugs", "how to buy drugs", "drug dealing instructions"],
    "unsafe practical activity or equipment": [
        "without adult supervision",
        "without safety goggles",
        "without protective gloves",
        "without ppe",
        "handle broken glass with bare hands",
        "taste the chemical",
        "inhale the fumes directly",
        "unsupervised experiment",
        "naked flame unattended",
    ],
    "activity requiring formal risk assessment or school permission": [
        "off-site visit",
        "off site trip",
        "school trip",
        "field trip",
        "requires parental consent",
        "requires signed permission",
        "offsite activity",
    ],
    "online safety or personal information risk": [
        "share your home address",
        "share your phone number",
        "post your full name online",
        "meet someone you met online",
        "share personal photos online",
        "share your password",
    ],
    "inappropriate one-to-one or physical contact": [
        "alone with a pupil",
        "one-to-one in a closed room",
        "physical restraint",
        "inappropriate touching",
    ],
    "bullying-related risk": [
        "encourage pupils to mock",
        "target a pupil publicly",
        "humiliate in front of the class",
        "single out a pupil to ridicule",
    ],
    "discriminatory or harmful content": [
        "certain races are inferior",
        "certain religions are wrong",
        "gender stereotypes are always true",
        "mock a pupil's disability",
    ],
}


def _all_text(content: LessonPlanContent, worksheet: WorksheetContent | None, homework_task: HomeworkContent | None) -> str:
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
    if worksheet is not None:
        parts.extend(
            [
                worksheet.title,
                worksheet.instructions,
                *worksheet.recall_questions,
                *worksheet.understanding_questions,
                *worksheet.application_questions,
                *worksheet.challenge_questions,
            ]
        )
    if homework_task is not None:
        parts.extend([homework_task.title, homework_task.instructions, *homework_task.tasks])
    return " ".join(parts).lower()


def scan_for_safeguarding_concerns(
    content: LessonPlanContent,
    worksheet: WorksheetContent | None = None,
    homework_task: HomeworkContent | None = None,
) -> tuple[bool, str | None]:
    """Returns (flagged, note). `note` is None when nothing was flagged.
    Scans the lesson content plus, when generated, the worksheet and
    homework -- a concerning term in either of those must surface the same
    review flag as one in the lesson body itself.
    """
    text = _all_text(content, worksheet, homework_task)
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
