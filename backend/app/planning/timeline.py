"""Validates and repairs the AI-generated timeline against the lesson's
actual duration. The model is asked to produce a timeline that spans the
full lesson, but nothing stops it from drifting -- this is the
deterministic check described in the brief: never trust generated output
at face value, validate it before saving.
"""

from app.schemas.lesson_plan_content import TimelineEntry


def normalize_timeline(entries: list[TimelineEntry], duration_minutes: int) -> list[TimelineEntry]:
    if not entries:
        return [TimelineEntry(start_minute=0, end_minute=duration_minutes, activity="Lesson", description="")]

    ordered = sorted(entries, key=lambda e: e.start_minute)
    total = sum(max(e.end_minute - e.start_minute, 0) for e in ordered) or 1
    scale = duration_minutes / total

    normalized: list[TimelineEntry] = []
    cursor = 0
    for entry in ordered:
        length = max(round((entry.end_minute - entry.start_minute) * scale), 1)
        start = cursor
        end = min(start + length, duration_minutes)
        normalized.append(TimelineEntry(start_minute=start, end_minute=end, activity=entry.activity, description=entry.description))
        cursor = end

    if normalized:
        normalized[-1].end_minute = duration_minutes

    return normalized
