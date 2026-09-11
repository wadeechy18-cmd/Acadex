"""Fixed lesson templates. Each is a proportional skeleton -- weights sum to
1.0 and get scaled to whatever duration the teacher actually picked, using
the largest-remainder method so the minutes always sum exactly to the
lesson's total (no silent 1-minute drift from naive rounding).
"""

import uuid

from app.models.lesson_plan import LessonPlanTemplateType
from app.schemas.lesson_plan import LessonSection

# (section_type, title, weight) -- weights within one template must sum to 1.0.
_TEMPLATE_SKELETONS: dict[LessonPlanTemplateType, list[tuple[str, str, float]]] = {
    LessonPlanTemplateType.STANDARD: [
        ("starter", "Starter", 0.1),
        ("retrieval_practice", "Retrieval Practice", 0.1),
        ("teacher_input", "Teacher Input", 0.2),
        ("guided_practice", "Guided Practice", 0.2),
        ("independent_practice", "Independent Practice", 0.2),
        ("assessment", "Assessment", 0.1),
        ("plenary", "Plenary", 0.1),
    ],
    LessonPlanTemplateType.PRACTICAL: [
        ("starter", "Starter", 0.1),
        ("safety_briefing", "Safety Briefing", 0.1),
        ("practical_activity", "Practical Activity", 0.5),
        ("recording_results", "Recording Results", 0.15),
        ("plenary", "Plenary", 0.15),
    ],
    LessonPlanTemplateType.REVISION: [
        ("starter", "Starter", 0.1),
        ("retrieval_practice", "Retrieval Practice", 0.3),
        ("exam_practice", "Exam Practice", 0.4),
        ("feedback", "Feedback", 0.1),
        ("plenary", "Plenary", 0.1),
    ],
    LessonPlanTemplateType.EXAM_PREP: [
        ("starter", "Starter", 0.1),
        ("exam_technique", "Exam Technique", 0.2),
        ("timed_practice", "Timed Practice", 0.5),
        ("peer_marking", "Peer Marking", 0.1),
        ("plenary", "Plenary", 0.1),
    ],
    LessonPlanTemplateType.NEW_TOPIC: [
        ("starter", "Starter", 0.1),
        ("hook", "Hook", 0.1),
        ("teacher_input", "Teacher Input", 0.3),
        ("guided_practice", "Guided Practice", 0.25),
        ("independent_practice", "Independent Practice", 0.15),
        ("plenary", "Plenary", 0.1),
    ],
    LessonPlanTemplateType.RETRIEVAL: [
        ("starter", "Starter", 0.15),
        ("retrieval_quiz", "Retrieval Quiz", 0.5),
        ("feedback", "Feedback", 0.2),
        ("plenary", "Plenary", 0.15),
    ],
    LessonPlanTemplateType.ASSESSMENT: [
        ("starter", "Starter", 0.1),
        ("instructions", "Instructions", 0.1),
        ("assessment", "Assessment", 0.7),
        ("plenary", "Plenary", 0.1),
    ],
    LessonPlanTemplateType.REVIEW: [
        ("starter", "Starter", 0.15),
        ("review_activity", "Review Activity", 0.55),
        ("discussion", "Discussion", 0.2),
        ("plenary", "Plenary", 0.1),
    ],
    LessonPlanTemplateType.DOUBLE: [
        ("starter", "Starter", 0.05),
        ("retrieval_practice", "Retrieval Practice", 0.1),
        ("teacher_input", "Teacher Input", 0.2),
        ("guided_practice", "Guided Practice", 0.2),
        ("independent_practice", "Independent Practice", 0.2),
        ("extended_practice", "Extended Practice", 0.15),
        ("plenary", "Plenary", 0.1),
    ],
    LessonPlanTemplateType.SHORT: [
        ("starter", "Starter", 0.15),
        ("teacher_input", "Teacher Input", 0.35),
        ("practice", "Practice", 0.35),
        ("plenary", "Plenary", 0.15),
    ],
}


def _allocate_minutes(weights: list[float], total_minutes: int) -> list[int]:
    """Largest-remainder rounding so the parts always sum exactly to
    total_minutes -- naive round() on each weight can drift by a minute or two.
    """
    raw = [w * total_minutes for w in weights]
    floors = [int(r) for r in raw]
    remainder = total_minutes - sum(floors)
    remainders = sorted(range(len(raw)), key=lambda i: raw[i] - floors[i], reverse=True)
    for i in remainders[:remainder]:
        floors[i] += 1
    return floors


def build_sections_from_template(template_type: LessonPlanTemplateType, duration_minutes: int) -> list[LessonSection]:
    skeleton = _TEMPLATE_SKELETONS[template_type]
    minutes = _allocate_minutes([w for _, _, w in skeleton], duration_minutes)
    return [
        LessonSection(id=str(uuid.uuid4()), type=section_type, title=title, duration_minutes=m, body=[])
        for (section_type, title, _), m in zip(skeleton, minutes)
    ]
