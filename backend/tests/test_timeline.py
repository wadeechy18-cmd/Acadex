from app.planning.timeline import normalize_timeline
from app.schemas.lesson_plan_content import TimelineEntry


def test_empty_timeline_gets_a_single_full_duration_fallback():
    result = normalize_timeline([], 30)
    assert len(result) == 1
    assert result[0].start_minute == 0
    assert result[0].end_minute == 30


def test_well_formed_timeline_matching_duration_is_left_intact():
    entries = [
        TimelineEntry(start_minute=0, end_minute=10, activity="A", description=""),
        TimelineEntry(start_minute=10, end_minute=30, activity="B", description=""),
    ]
    result = normalize_timeline(entries, 30)
    assert result[0].start_minute == 0
    assert result[0].end_minute == 10
    assert result[-1].end_minute == 30


def test_overrunning_timeline_is_scaled_down_to_fit():
    entries = [
        TimelineEntry(start_minute=0, end_minute=30, activity="A", description=""),
        TimelineEntry(start_minute=30, end_minute=60, activity="B", description=""),
    ]
    result = normalize_timeline(entries, 30)
    assert result[0].start_minute == 0
    assert result[-1].end_minute == 30
    assert all(e.end_minute <= 30 for e in result)


def test_timeline_entries_stay_contiguous_after_normalization():
    entries = [
        TimelineEntry(start_minute=5, end_minute=8, activity="A", description=""),
        TimelineEntry(start_minute=0, end_minute=2, activity="B", description=""),  # out of order on purpose
    ]
    result = normalize_timeline(entries, 20)
    for prev, curr in zip(result, result[1:]):
        assert curr.start_minute == prev.end_minute
