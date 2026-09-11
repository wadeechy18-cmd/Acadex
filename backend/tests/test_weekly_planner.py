import uuid
from datetime import time

from app.models.weekly_plan import DayOfWeek
from app.planning.weekly_planner import (
    analyze_week,
    detect_gaps,
    detect_missing_assessment,
    detect_overload,
    detect_repeated_topics,
    detect_time_conflicts,
)
from app.schemas.weekly_plan import WeeklyPlanItemView


def _item(**overrides) -> WeeklyPlanItemView:
    defaults = dict(
        id=uuid.uuid4(),
        class_id=uuid.uuid4(),
        class_name="9C Chemistry",
        lesson_plan_id=None,
        topic="Atomic structure",
        template_type="standard",
        day_of_week=DayOfWeek.MONDAY,
        start_time=time(9, 0),
        duration_minutes=50,
    )
    defaults.update(overrides)
    return WeeklyPlanItemView(**defaults)


def test_detect_time_conflicts_flags_overlapping_sessions_same_day():
    a = _item(start_time=time(9, 0), duration_minutes=60, class_name="9C Chemistry")
    b = _item(start_time=time(9, 30), duration_minutes=30, class_name="10A Physics")
    issues = detect_time_conflicts([a, b])
    assert len(issues) == 1
    assert issues[0].category == "conflict"
    assert issues[0].severity == "warning"
    assert set(issues[0].item_ids) == {a.id, b.id}


def test_detect_time_conflicts_ignores_back_to_back_sessions():
    a = _item(start_time=time(9, 0), duration_minutes=60)
    b = _item(start_time=time(10, 0), duration_minutes=30)  # starts exactly when `a` ends
    assert detect_time_conflicts([a, b]) == []


def test_detect_time_conflicts_ignores_different_days():
    a = _item(start_time=time(9, 0), duration_minutes=60, day_of_week=DayOfWeek.MONDAY)
    b = _item(start_time=time(9, 0), duration_minutes=60, day_of_week=DayOfWeek.TUESDAY)
    assert detect_time_conflicts([a, b]) == []


def test_detect_overload_flags_a_day_over_the_minute_threshold():
    items = [_item(day_of_week=DayOfWeek.MONDAY, start_time=time(9 + i, 0), duration_minutes=60) for i in range(6)]
    issues = detect_overload(items)
    assert len(issues) == 1
    assert issues[0].category == "overload"
    assert issues[0].day_of_week == DayOfWeek.MONDAY


def test_detect_overload_does_not_flag_a_normal_day():
    items = [_item(day_of_week=DayOfWeek.MONDAY, start_time=time(9, 0), duration_minutes=50)]
    assert detect_overload(items) == []


def test_detect_gaps_flags_weekdays_with_nothing_scheduled():
    items = [_item(day_of_week=DayOfWeek.MONDAY)]
    issues = detect_gaps(items)
    flagged_days = {i.day_of_week for i in issues}
    assert flagged_days == {DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY}
    assert all(i.severity == "info" for i in issues)


def test_detect_gaps_returns_nothing_for_a_completely_empty_week():
    """An unstarted week isn't a "gap" -- nothing to flag until planning begins."""
    assert detect_gaps([]) == []


def test_detect_repeated_topics_flags_the_same_topic_scheduled_twice():
    a = _item(topic="Photosynthesis", day_of_week=DayOfWeek.MONDAY)
    b = _item(topic="photosynthesis", day_of_week=DayOfWeek.WEDNESDAY)  # case-insensitive match
    issues = detect_repeated_topics([a, b])
    assert len(issues) == 1
    assert issues[0].category == "repeated_topic"
    assert set(issues[0].item_ids) == {a.id, b.id}


def test_detect_repeated_topics_ignores_unique_topics():
    a = _item(topic="Photosynthesis")
    b = _item(topic="Cell division")
    assert detect_repeated_topics([a, b]) == []


def test_detect_missing_assessment_nudges_after_three_sessions_with_none():
    class_id = uuid.uuid4()
    items = [_item(class_id=class_id, template_type="standard", day_of_week=d) for d in list(DayOfWeek)[:3]]
    issues = detect_missing_assessment(items)
    assert len(issues) == 1
    assert issues[0].category == "missing_assessment"


def test_detect_missing_assessment_says_nothing_when_an_assessment_exists():
    class_id = uuid.uuid4()
    items = [_item(class_id=class_id, template_type="standard", day_of_week=d) for d in list(DayOfWeek)[:2]]
    items.append(_item(class_id=class_id, template_type="assessment", day_of_week=list(DayOfWeek)[2]))
    assert detect_missing_assessment(items) == []


def test_detect_missing_assessment_says_nothing_for_light_weeks():
    class_id = uuid.uuid4()
    items = [_item(class_id=class_id, template_type="standard", day_of_week=DayOfWeek.MONDAY)]
    assert detect_missing_assessment(items) == []


def test_analyze_week_combines_every_check():
    conflict_a = _item(start_time=time(9, 0), duration_minutes=60, day_of_week=DayOfWeek.MONDAY)
    conflict_b = _item(start_time=time(9, 30), duration_minutes=30, day_of_week=DayOfWeek.MONDAY)
    issues = analyze_week([conflict_a, conflict_b])
    categories = {i.category for i in issues}
    assert "conflict" in categories
    assert "gap" in categories  # Tue-Fri still empty
