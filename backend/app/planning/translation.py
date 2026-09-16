"""Bangla translation of a lesson's content -- one AI call producing the
same structured shape as the English original (see
app.schemas.lesson_plan_content.TranslatedContent), stored alongside it and
never overwriting it. See app/services/lesson_plan_service.py's
translate_version for caching (translation only happens once per version
unless explicitly re-requested).
"""

from app.ai.provider import AIProvider
from app.schemas.lesson_plan_content import HomeworkContent, LessonPlanContent, TranslatedContent, WorksheetContent

TRANSLATION_SYSTEM_PROMPT = """You are Acadex, translating a primary school lesson plan -- and, where \
given, its worksheet and homework -- from English into Bangla (বাংলা), for a teacher who wants a Bangla \
version alongside the English original. Produce JSON matching the required schema exactly.

Rules:
- Translate every piece of teaching text (titles, instructions, objectives, explanations, questions, \
differentiation, misconceptions, etc.) into natural, correct Bangla that preserves the educational meaning.
- Where a "teacher_says" field is present, translate it as something a teacher would actually say out \
loud to a class in Bangla -- natural spoken classroom Bangla, never a stiff word-for-word rendering.
- Do NOT translate: chemical formulas, mathematical formulas, units of measurement, numbers, symbols, or \
curriculum codes.
- For subject-specific technical terms, give the Bangla term followed by the English term in brackets, \
e.g. "সালোকসংশ্লেষণ (Photosynthesis)", so the teacher can cross-reference both.
- Keep exactly the same structure as the English input (the same number of items in every list, the same \
number of timeline entries) -- translate the text, never add, remove, reorder, or summarize items.
"""


def translate_content(
    ai_provider: AIProvider,
    content: LessonPlanContent,
    worksheet: WorksheetContent | None,
    homework_task: HomeworkContent | None,
) -> TranslatedContent:
    lines = ["Translate the following lesson plan content to Bangla.", "Lesson:", content.model_dump_json(indent=2)]
    if worksheet is not None:
        lines += ["Worksheet:", worksheet.model_dump_json(indent=2)]
    if homework_task is not None:
        lines += ["Homework:", homework_task.model_dump_json(indent=2)]
    prompt = "\n".join(lines)

    result = ai_provider.generate_structured(system=TRANSLATION_SYSTEM_PROMPT, prompt=prompt, schema=TranslatedContent)
    return result.parsed
