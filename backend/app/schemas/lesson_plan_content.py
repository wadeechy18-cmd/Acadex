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


class TeacherScriptSection(BaseModel):
    """A section a teacher can read straight off the screen and teach from,
    rather than a paragraph they have to translate into action themselves.
    Every field is optional-in-practice (empty string/list when nothing
    applies to this section) so a section that's genuinely just an
    activity with no dialogue doesn't need invented lines.
    """

    teacher_says: str = ""
    ask: list[str] = Field(default_factory=list)
    expected_answers: list[str] = Field(default_factory=list)
    do: str = ""
    students_do: str = ""
    check_understanding: str = ""
    watch_out_for: str = ""


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
    # Classroom-script breakdown of four sections -- additive and optional
    # so a plan generated (or imported into the library) before this
    # existed still loads and renders fine via the plain string fields
    # above, which always stay populated as a fallback/summary.
    starter_script: TeacherScriptSection | None = None
    teacher_explanation_script: TeacherScriptSection | None = None
    guided_practice_script: TeacherScriptSection | None = None
    plenary_script: TeacherScriptSection | None = None


class WorksheetContent(BaseModel):
    """A worksheet generated alongside the lesson plan, based on the same
    topic and retrieved resources -- never a separate ask from the teacher.
    Questions are grouped by cognitive demand rather than left as one flat
    list, matching how a teacher actually picks which ones to set.
    """

    title: str
    instructions: str
    recall_questions: list[str]
    understanding_questions: list[str]
    application_questions: list[str]
    challenge_questions: list[str]


class HomeworkContent(BaseModel):
    """Homework generated alongside the lesson plan to reinforce what was
    taught -- distinct from LessonPlanContent.homework, which stays a short
    in-plan note; this is the full standalone task sheet.
    """

    title: str
    instructions: str
    tasks: list[str]
    estimated_minutes: int


class TranslatedContent(BaseModel):
    """A Bangla translation of one version's full content, stored alongside
    (never over) the English original -- see app/planning/translation.py.
    """

    lesson: LessonPlanContent
    worksheet: WorksheetContent | None = None
    homework: HomeworkContent | None = None


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
    "starter_script": TeacherScriptSection,
    "teacher_explanation_script": TeacherScriptSection,
    "guided_practice_script": TeacherScriptSection,
    "plenary_script": TeacherScriptSection,
}
