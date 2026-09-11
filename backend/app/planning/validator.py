"""Pre-display lesson-quality checks -- all fixed Python rules, no AI. See
docs/LESSON_PLANNER_ARCHITECTURE.md section 14 for why the safeguarding flag
here is a keyword match, never a model judgment call: it only ever surfaces
the standard "follow your school's procedure" note, and never tells a
teacher a concern is or isn't real.
"""

from typing import Literal

from pydantic import BaseModel

from app.models.lesson_plan import LessonPlanTemplateType
from app.planning.timing import TimingCheck, check_timing
from app.schemas.lesson_plan import LessonPlanContent

# Deliberately narrow and specific -- broad words like "bullying" or "drugs"
# would false-positive on ordinary PSHE/biology curriculum content. This list
# only ever triggers a standard escalation note; it never blocks saving or
# publishing a plan.
SAFEGUARDING_KEYWORDS = [
    "self-harm", "self harm", "suicide", "grooming", "domestic violence",
    "female genital mutilation", "fgm", "radicalisation", "radicalization",
    "extremism", "child exploitation", "county lines", "sexual abuse",
    "sexual assault", "neglect",
]

SAFEGUARDING_NOTE = (
    "This topic may touch on a safeguarding-sensitive area. Check your school's "
    "safeguarding policy and follow the school's established DSL procedure if a "
    "pupil discloses a concern during this lesson."
)

# Template types where the brief expects a dedicated assessment component.
_TEMPLATES_REQUIRING_ASSESSMENT = {LessonPlanTemplateType.ASSESSMENT, LessonPlanTemplateType.EXAM_PREP}


class QualityIssue(BaseModel):
    severity: Literal["info", "warning"]
    message: str


class LessonPlanQualityReport(BaseModel):
    timing: TimingCheck
    issues: list[QualityIssue]


def is_safeguarding_sensitive(topic: str, title: str) -> bool:
    haystack = f"{topic} {title}".lower()
    return any(keyword in haystack for keyword in SAFEGUARDING_KEYWORDS)


def validate_lesson_plan(
    *, title: str, topic: str, duration_minutes: int, template_type: LessonPlanTemplateType, content: LessonPlanContent
) -> LessonPlanQualityReport:
    timing = check_timing(content.sections, duration_minutes)
    issues: list[QualityIssue] = []

    if timing.status != "ok":
        word = "under" if timing.status == "under" else "over"
        issues.append(
            QualityIssue(
                severity="warning",
                message=f"Sections {word}-run the planned length by {abs(timing.difference_minutes)} minute(s).",
            )
        )

    if not content.learning_objectives:
        issues.append(QualityIssue(severity="warning", message="No learning objectives have been set yet."))

    if not content.sections:
        issues.append(QualityIssue(severity="warning", message="This lesson has no sections yet."))

    has_assessment_section = any("assessment" in s.type.lower() or "assessment" in s.title.lower() for s in content.sections)
    if template_type in _TEMPLATES_REQUIRING_ASSESSMENT and not has_assessment_section:
        issues.append(
            QualityIssue(severity="warning", message=f"A {template_type.value.replace('_', ' ')} lesson usually needs an assessment section.")
        )
    elif not has_assessment_section and not content.assessment_for_learning:
        issues.append(QualityIssue(severity="info", message="No assessment section or assessment-for-learning notes yet."))

    if is_safeguarding_sensitive(topic, title):
        issues.append(QualityIssue(severity="info", message=SAFEGUARDING_NOTE))

    return LessonPlanQualityReport(timing=timing, issues=issues)
