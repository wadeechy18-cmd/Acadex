"""Deterministic resolution of the date phrases teachers actually type
("tomorrow", "next Monday", "15 September") into a real calendar date.
Pure Python -- the AI request-interpretation step only ever extracts the
raw phrase; it never computes or is trusted with the actual date, since an
LLM has no reliable notion of "today" on its own.
"""

import re
from datetime import date, timedelta

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

_TODAY_PHRASES = {"today", "this morning", "this afternoon", "later today"}
_TOMORROW_PHRASES = {"tomorrow"}
_DAY_AFTER_PHRASES = {"day after tomorrow", "the day after tomorrow"}


def resolve_relative_date(phrase: str | None, today: date) -> date | None:
    """Returns None when the phrase is empty or not understood -- callers
    treat that as "no date given", never a guess.
    """
    if not phrase:
        return None
    normalized = re.sub(r"\s+", " ", phrase.strip().lower())

    if normalized in _TODAY_PHRASES:
        return today
    if normalized in _TOMORROW_PHRASES:
        return today + timedelta(days=1)
    if normalized in _DAY_AFTER_PHRASES:
        return today + timedelta(days=2)

    for i, weekday_name in enumerate(_WEEKDAYS):
        if weekday_name in normalized:
            days_ahead = (i - today.weekday()) % 7
            if days_ahead == 0 and "this" not in normalized:
                days_ahead = 7  # "Monday" / "next Monday" means the coming one, not today
            return today + timedelta(days=days_ahead)

    try:
        return date.fromisoformat(normalized)
    except ValueError:
        return None
