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

from app.schemas.lesson_plan_content import HomeworkContent, LessonPlanContent, TeacherScriptSection, WorksheetContent

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


def _script_text(script: TeacherScriptSection | None) -> list[str]:
    if script is None:
        return []
    return [script.teacher_says, *script.ask, *script.expected_answers, script.do, script.students_do, script.check_understanding, script.watch_out_for]


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
        *_script_text(content.starter_script),
        *_script_text(content.teacher_explanation_script),
        *_script_text(content.guided_practice_script),
        *_script_text(content.plenary_script),
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


# What a flagged category actually means for the teacher, plus one concrete,
# generally-applicable safer alternative -- so the note tells them something
# useful to act on, not just a category name. This is still a fixed,
# deterministic mapping (the same "flag, never decide" principle as the
# keyword list itself), not a judgement call about this specific lesson.
_CATEGORY_GUIDANCE: dict[str, str] = {
    "self-harm or suicide": (
        "This lesson may reference self-harm or suicide. Safer option: remove this content and consult "
        "your school's designated safeguarding lead before teaching anything on this topic."
    ),
    "weapons or violent instructions": (
        "This lesson may include instructions for making a weapon. Safer option: replace with a "
        "description or diagram that does not give working, reproducible instructions."
    ),
    "sexual content": (
        "This lesson may include sexual content. Safer option: remove it and check it is age-appropriate "
        "against your school's RSE (relationships and sex education) policy before teaching it."
    ),
    "extremism or hate": (
        "This lesson may include extremist or hateful content. Safer option: remove it and raise it with "
        "your school's safeguarding lead -- this can be relevant even in a history or current-affairs context."
    ),
    "substance misuse instructions": (
        "This lesson may include instructions related to drug use or acquisition. Safer option: keep any "
        "discussion of substances at an educational, non-instructional level (effects and risks, not how-to)."
    ),
    "unsafe practical activity or equipment": (
        "This lesson involves equipment or a practical activity without a stated safety precaution (e.g. "
        "supervision or protective equipment). Safer option: add explicit supervision/PPE instructions, or "
        "substitute a lower-risk version (e.g. pre-cut materials instead of pupils using scissors unsupervised)."
    ),
    "activity requiring formal risk assessment or school permission": (
        "This lesson involves an off-site visit or an activity that normally needs a formal risk assessment "
        "or parental consent. Safer option: check this has been through your school's usual approval process "
        "before running it, or adapt the activity to stay on-site."
    ),
    "online safety or personal information risk": (
        "This lesson may ask pupils to share personal information online or contact someone online. Safer "
        "option: remove any request for personal details and use a controlled, teacher-supervised example instead."
    ),
    "inappropriate one-to-one or physical contact": (
        "This lesson describes a one-to-one or physical-contact situation. Safer option: keep interactions "
        "visible/in open spaces and follow your school's safer-working-practice policy."
    ),
    "bullying-related risk": (
        "This lesson may single out or humiliate a pupil in front of the class. Safer option: rephrase the "
        "activity so no individual pupil is put on the spot or mocked."
    ),
    "discriminatory or harmful content": (
        "This lesson may include discriminatory or stereotyped content. Safer option: rewrite it to challenge "
        "rather than state the stereotype, or remove it."
    ),
}


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

    guidance = [
        f"{category}: {_CATEGORY_GUIDANCE.get(category, 'possible concern area -- review before use.')}"
        for category in matched_categories
    ]
    note = " ".join(guidance) + (
        " This is a keyword-based software check only, not a substitute for your school's safeguarding "
        "policy or your own professional judgement -- it does not guarantee the content is safe or "
        "unsafe, only that it may be worth a closer look."
    )
    return True, note
