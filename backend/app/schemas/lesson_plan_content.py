"""The structured shape every generated (or hand-written) lesson plan's
content takes -- a JSON object with named sections, never one text blob.
This is what the AI provider is asked to fill in (see
app/planning/lesson_generation.py) and what LessonPlanVersion.content
stores.
"""

from pydantic import BaseModel, Field


class TimelineEntry(BaseModel):
    start_minute: int = Field(ge=0)
    end_minute: int = Field(ge=0)
    activity: str
    description: str


class Differentiation(BaseModel):
    support: str
    core: str
    greater_depth: str


class LessonPlanContent(BaseModel):
    title: str
    overview: str
    learning_objectives: list[str]
    success_criteria: list[str]
    key_vocabulary: list[str]
    prior_knowledge: str
    resources_needed: list[str]
    starter: str
    teacher_explanation: str
    guided_practice: str
    independent_practice: str
    key_questions: list[str]
    differentiation: Differentiation
    assessment: str
    misconceptions: list[str]
    plenary: str
    homework: str
    cross_curricular_links: str
    timeline: list[TimelineEntry]


# Sections a teacher can ask Acadex to regenerate individually -- title is
# trivial to hand-edit and is excluded so "regenerate" always means
# regenerating substantive content, never just the name.
REGENERATABLE_SECTIONS: dict[str, type] = {
    "overview": str,
    "learning_objectives": list[str],
    "success_criteria": list[str],
    "key_vocabulary": list[str],
    "prior_knowledge": str,
    "resources_needed": list[str],
    "starter": str,
    "teacher_explanation": str,
    "guided_practice": str,
    "independent_practice": str,
    "key_questions": list[str],
    "differentiation": Differentiation,
    "assessment": str,
    "misconceptions": list[str],
    "plenary": str,
    "homework": str,
    "cross_curricular_links": str,
    "timeline": list[TimelineEntry],
}
