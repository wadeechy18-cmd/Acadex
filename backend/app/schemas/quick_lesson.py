"""The simple natural-language entry point: a teacher types one sentence,
Acadex extracts structured intent from it (via one small AI call -- see
INTENT_SYSTEM_PROMPT in app/planning/lesson_generation.py), then Python
(app/planning/date_resolution.py, app/planning/entity_matching.py) resolves
that intent against real data before any lesson content is generated.
"""

from pydantic import BaseModel, Field


class QuickLessonIntent(BaseModel):
    subject_name: str | None = None
    year_group_or_key_stage: str | None = None
    topic: str
    relative_date_phrase: str | None = None
    duration_minutes: int | None = None
    ability_level: str | None = None
    additional_instructions: str | None = None


class QuickGenerateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
