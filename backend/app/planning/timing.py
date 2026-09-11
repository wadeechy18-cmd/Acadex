"""Duration-sum validation and gap-filling suggestions -- pure arithmetic,
never an LLM call. Mirrors the worked example in the product brief: a
50-minute lesson whose sections sum to 45 gets a "5 minutes remaining" flag
plus concrete suggestions (extend an existing section, or add a new one),
not just a bare warning.
"""

import uuid
from typing import Literal

from pydantic import BaseModel

from app.schemas.lesson_plan import LessonSection

# Priority order for "which existing section should absorb a time gap" --
# a practice slot is the least disruptive place to add time, then
# assessment, then plenary, before falling back to whatever's last.
_EXTEND_PRIORITY = ("practice", "assessment", "plenary")


class TimingSuggestion(BaseModel):
    label: str
    action: Literal["extend_section", "add_section"]
    section_id: str | None = None
    extend_by_minutes: int | None = None
    new_section: LessonSection | None = None


class TimingCheck(BaseModel):
    total_minutes: int
    planned_minutes: int
    difference_minutes: int  # positive = under time, negative = over time
    status: Literal["ok", "under", "over"]
    suggestions: list[TimingSuggestion] = []


def _matching_sections(sections: list[LessonSection], keyword: str) -> list[LessonSection]:
    return [s for s in sections if keyword in s.type.lower() or keyword in s.title.lower()]


def check_timing(sections: list[LessonSection], planned_minutes: int) -> TimingCheck:
    total = sum(s.duration_minutes for s in sections)
    difference = planned_minutes - total

    if difference == 0:
        return TimingCheck(total_minutes=total, planned_minutes=planned_minutes, difference_minutes=0, status="ok")

    if difference > 0:
        suggestions: list[TimingSuggestion] = []
        suggested_section_ids: set[str] = set()
        for keyword in _EXTEND_PRIORITY:
            for section in _matching_sections(sections, keyword):
                if section.id in suggested_section_ids:
                    continue  # a section matching multiple keywords (e.g. "Practice Assessment") gets one suggestion, not one per keyword
                suggestions.append(
                    TimingSuggestion(
                        label=f"Extend {section.title}",
                        action="extend_section",
                        section_id=section.id,
                        extend_by_minutes=difference,
                    )
                )
                suggested_section_ids.add(section.id)
        matched_any = bool(suggested_section_ids)
        if not matched_any and sections:
            last = sections[-1]
            suggestions.append(
                TimingSuggestion(
                    label=f"Extend {last.title}",
                    action="extend_section",
                    section_id=last.id,
                    extend_by_minutes=difference,
                )
            )
        suggestions.append(
            TimingSuggestion(
                label="Add Practice",
                action="add_section",
                new_section=LessonSection(
                    id=str(uuid.uuid4()), type="practice", title="Practice", duration_minutes=difference, body=[]
                ),
            )
        )
        return TimingCheck(
            total_minutes=total, planned_minutes=planned_minutes, difference_minutes=difference,
            status="under", suggestions=suggestions,
        )

    # Over time: suggest shortening the single longest section.
    suggestions = []
    if sections:
        longest = max(sections, key=lambda s: s.duration_minutes)
        shorten_by = min(-difference, longest.duration_minutes)
        suggestions.append(
            TimingSuggestion(
                label=f"Shorten {longest.title}",
                action="extend_section",
                section_id=longest.id,
                extend_by_minutes=-shorten_by,
            )
        )
    return TimingCheck(
        total_minutes=total, planned_minutes=planned_minutes, difference_minutes=difference,
        status="over", suggestions=suggestions,
    )
