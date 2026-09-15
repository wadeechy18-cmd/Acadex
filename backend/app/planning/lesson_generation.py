"""Pure prompt-construction logic for the AI Lesson Plan Builder. No DB
access and no AI provider calls here -- see app/services/lesson_plan_service.py
for the orchestration that calls these builders, then the AIProvider, then
app/planning/timeline.py and app/planning/safeguarding.py to validate the
result before it's ever saved.
"""

SYSTEM_PROMPT = """You are Acadex, an assistant that helps primary school teachers in England \
plan high-quality, curriculum-aligned lessons. You will be given the subject, year group, \
topic and duration for a single lesson, and must produce a complete, structured lesson plan \
as JSON matching the required schema exactly -- never a single block of prose.

Rules:
- Write for the stated year group's reading age and attention span.
- The "timeline" must be a sequence of short, sequential activities whose start_minute and \
end_minute values run from 0 to the lesson's full duration with no gaps or overlaps.
- Differentiation must give genuinely different tasks or scaffolding for "support", "core" and \
"greater_depth" pupils, not just the same task with a different label.
- Content must always be age-appropriate. Never include anything violent, sexual, frightening, \
or otherwise unsuitable for the stated year group, even if a resource or instruction suggests it.
- If resource excerpts are provided, actively draw on them (their content, vocabulary, examples) \
rather than ignoring them.
"""


def build_generation_prompt(
    *,
    curriculum_name: str,
    key_stage_name: str,
    year_group_name: str,
    subject_name: str,
    topic_title: str,
    duration_minutes: int,
    ability_level: str,
    curriculum_objectives: list[str],
    teacher_objectives: str | None,
    instructions: str | None,
    resource_excerpts: list[tuple[str, str]],
) -> str:
    lines = [
        f"Curriculum: {curriculum_name}",
        f"Key stage: {key_stage_name}",
        f"Year group: {year_group_name}",
        f"Subject: {subject_name}",
        f"Topic: {topic_title}",
        f"Lesson duration: {duration_minutes} minutes",
        f"Target ability level: {ability_level}",
    ]

    if curriculum_objectives:
        lines.append("Curriculum objectives to cover:")
        lines.extend(f"- {obj}" for obj in curriculum_objectives)

    if teacher_objectives:
        lines.append(f"Additional objectives specified by the teacher: {teacher_objectives}")

    if instructions:
        lines.append(f"Additional instructions from the teacher: {instructions}")

    if resource_excerpts:
        lines.append("The teacher has attached the following resources -- use their content where relevant:")
        for name, excerpt in resource_excerpts:
            lines.append(f"--- Resource: {name} ---\n{excerpt}")

    lines.append("Produce the full lesson plan now, matching the required JSON schema exactly.")
    return "\n".join(lines)


def build_regeneration_prompt(
    *,
    section_name: str,
    current_content_json: str,
    extra_instructions: str | None,
) -> str:
    lines = [
        "Here is the full current lesson plan, as JSON, for context:",
        current_content_json,
        "",
        f'Regenerate ONLY the "{section_name}" section. It must stay consistent with every other '
        "section shown above (same topic, duration, timeline boundaries, and ability level) -- do not "
        "change anything else, and do not explain your answer, just return the new value for this section.",
    ]
    if extra_instructions:
        lines.append(f"Additional instruction for this regeneration: {extra_instructions}")
    return "\n".join(lines)


INTENT_SYSTEM_PROMPT = """You are Acadex's request interpreter. A primary school teacher in England has \
typed a short, casual request for a lesson. Extract structured fields from it as JSON matching the \
required schema exactly. Do not generate any lesson content here -- only extract what the teacher said.

Rules:
- Never invent a value for a field the teacher did not mention -- leave it null.
- "subject_name" and "year_group_or_key_stage" should be the teacher's own wording (e.g. "science", \
"early years", "Year 2"), not a curriculum code.
- "relative_date_phrase" is the teacher's own date wording verbatim (e.g. "tomorrow", "next Monday", \
"15 September"), or null if no date was mentioned.
- "topic" is required. If the teacher didn't name a specific curriculum topic, use their general \
description of what they want to teach as the topic.
- "ability_level" must be one of "support", "core", "greater_depth", "mixed" if and only if the teacher's \
wording clearly implies one of those; otherwise null.
"""

WORKSHEET_SYSTEM_PROMPT = """You are Acadex, generating a pupil worksheet to accompany a lesson plan you \
have already produced for a primary school teacher in England. Produce a worksheet as JSON matching the \
required schema exactly.

Rules:
- Every question must be based on the lesson's topic, objectives and (if given) the resource excerpts -- \
never introduce unrelated material just to fill a section.
- "recall_questions" test remembering facts/vocabulary just taught. "understanding_questions" test \
explaining ideas in the pupil's own words. "application_questions" ask pupils to use the idea in a new \
situation. "challenge_questions" go beyond the core lesson for pupils who finish early -- it is fine for \
this list to be shorter than the others, or empty if genuinely nothing suitable applies.
- Write for the stated year group's reading age.
"""

HOMEWORK_SYSTEM_PROMPT = """You are Acadex, generating homework to accompany a lesson plan you have \
already produced for a primary school teacher in England. Produce homework as JSON matching the required \
schema exactly.

Rules:
- Homework must reinforce what was taught in this specific lesson -- never introduce a new topic.
- Tasks must be appropriate for independent work at home without a teacher present.
- estimated_minutes must be a realistic, honest estimate for the stated year group, not a round default.
"""


def build_worksheet_prompt(
    *,
    subject_name: str,
    year_group_name: str,
    topic_title: str,
    lesson_overview: str,
    learning_objectives: list[str],
    resource_excerpts: list[tuple[str, str]],
) -> str:
    lines = [
        f"Subject: {subject_name}",
        f"Year group: {year_group_name}",
        f"Topic: {topic_title}",
        f"Lesson overview: {lesson_overview}",
        "Learning objectives:",
        *[f"- {obj}" for obj in learning_objectives],
    ]
    if resource_excerpts:
        lines.append("The teacher's own resources for this lesson -- draw questions from their content where relevant:")
        for name, excerpt in resource_excerpts:
            lines.append(f"--- Resource: {name} ---\n{excerpt}")
    lines.append("Produce the worksheet now, matching the required JSON schema exactly.")
    return "\n".join(lines)


def build_homework_prompt(
    *,
    subject_name: str,
    year_group_name: str,
    topic_title: str,
    lesson_overview: str,
    learning_objectives: list[str],
    resource_excerpts: list[tuple[str, str]],
) -> str:
    lines = [
        f"Subject: {subject_name}",
        f"Year group: {year_group_name}",
        f"Topic: {topic_title}",
        f"Lesson overview: {lesson_overview}",
        "Learning objectives covered in the lesson:",
        *[f"- {obj}" for obj in learning_objectives],
    ]
    if resource_excerpts:
        lines.append("The teacher's own resources for this lesson -- draw tasks from their content where relevant:")
        for name, excerpt in resource_excerpts:
            lines.append(f"--- Resource: {name} ---\n{excerpt}")
    lines.append("Produce the homework now, matching the required JSON schema exactly.")
    return "\n".join(lines)


MAX_RESOURCE_EXCERPT_CHARS = 2000
MAX_TOTAL_RESOURCE_CHARS = 6000


def build_resource_excerpts(resources: list[tuple[str, str | None]]) -> list[tuple[str, str]]:
    """`resources` is a list of (display_name, extracted_text | None). Skips
    resources with no extracted text (failed extraction, or an image) and
    caps both per-resource and total injected length so one huge document
    can't blow out the prompt.
    """
    excerpts: list[tuple[str, str]] = []
    remaining = MAX_TOTAL_RESOURCE_CHARS
    for name, text in resources:
        if not text or remaining <= 0:
            continue
        excerpt = text[: min(MAX_RESOURCE_EXCERPT_CHARS, remaining)]
        excerpts.append((name, excerpt))
        remaining -= len(excerpt)
    return excerpts
