from datetime import date

from app.planning.date_resolution import resolve_relative_date

MONDAY = date(2026, 9, 14)  # a known Monday


def test_none_or_empty_phrase_resolves_to_none():
    assert resolve_relative_date(None, MONDAY) is None
    assert resolve_relative_date("", MONDAY) is None


def test_today_and_tomorrow():
    assert resolve_relative_date("today", MONDAY) == MONDAY
    assert resolve_relative_date("Tomorrow", MONDAY) == date(2026, 9, 15)


def test_day_after_tomorrow():
    assert resolve_relative_date("day after tomorrow", MONDAY) == date(2026, 9, 16)


def test_named_weekday_resolves_to_the_coming_occurrence():
    # Monday itself, asking for "Wednesday" -> two days ahead.
    assert resolve_relative_date("Wednesday", MONDAY) == date(2026, 9, 16)
    # Asking for "Monday" (the same day) means next week's Monday, not today.
    assert resolve_relative_date("Monday", MONDAY) == date(2026, 9, 21)
    assert resolve_relative_date("next monday", MONDAY) == date(2026, 9, 21)


def test_explicit_iso_date_passes_through():
    assert resolve_relative_date("2026-12-25", MONDAY) == date(2026, 12, 25)


def test_unrecognized_phrase_resolves_to_none():
    assert resolve_relative_date("sometime next term", MONDAY) is None
