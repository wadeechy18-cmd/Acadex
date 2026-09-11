"""Schedule-gap/overload/conflict/repeated-topic/missing-assessment
detection over a teacher's weekly plan -- pure Python, no AI, no database
access. Operates on WeeklyPlanItemView, the same denormalised shape the API
returns, so this module is trivially unit-testable without a database.
"""

from collections import defaultdict

from app.models.weekly_plan import DayOfWeek
from app.schemas.weekly_plan import WeeklyPlanIssue, WeeklyPlanItemView

_SCHOOL_WEEKDAYS = (
    DayOfWeek.MONDAY,
    DayOfWeek.TUESDAY,
    DayOfWeek.WEDNESDAY,
    DayOfWeek.THURSDAY,
    DayOfWeek.FRIDAY,
)

# Deliberately generous fixed thresholds -- flags an unusually packed day
# without knowing a school's actual timetable structure. A teacher can
# always ignore the suggestion; it's advisory, never a hard limit.
_MAX_MINUTES_PER_DAY = 300
_MAX_SESSIONS_PER_DAY = 6

# A class taught this many times in one week with no assessment-type
# session is worth a nudge -- not a rule, since not every week needs one.
_MIN_SESSIONS_BEFORE_ASSESSMENT_NUDGE = 3


def _minutes(t) -> int:
    return t.hour * 60 + t.minute


def _by_day(items: list[WeeklyPlanItemView]) -> dict[DayOfWeek, list[WeeklyPlanItemView]]:
    grouped: dict[DayOfWeek, list[WeeklyPlanItemView]] = defaultdict(list)
    for item in items:
        grouped[item.day_of_week].append(item)
    return grouped


def detect_time_conflicts(items: list[WeeklyPlanItemView]) -> list[WeeklyPlanIssue]:
    """Two different classes double-booked at overlapping times on the same
    day -- the clearest, least ambiguous meaning of "overload" for a single
    teacher's timetable.
    """
    issues = []
    for day, day_items in _by_day(items).items():
        ordered = sorted(day_items, key=lambda i: _minutes(i.start_time))
        for i, first in enumerate(ordered):
            first_end = _minutes(first.start_time) + first.duration_minutes
            for second in ordered[i + 1 :]:
                second_start = _minutes(second.start_time)
                if second_start >= first_end:
                    break  # sorted by start time -- nothing further can overlap `first`
                issues.append(
                    WeeklyPlanIssue(
                        category="conflict",
                        severity="warning",
                        message=f"{first.class_name} and {second.class_name} overlap on {day.value}.",
                        day_of_week=day,
                        item_ids=[first.id, second.id],
                    )
                )
    return issues


def detect_overload(items: list[WeeklyPlanItemView]) -> list[WeeklyPlanIssue]:
    issues = []
    for day, day_items in _by_day(items).items():
        total_minutes = sum(i.duration_minutes for i in day_items)
        if total_minutes > _MAX_MINUTES_PER_DAY or len(day_items) > _MAX_SESSIONS_PER_DAY:
            issues.append(
                WeeklyPlanIssue(
                    category="overload",
                    severity="warning",
                    message=(
                        f"{day.value.capitalize()} looks heavily loaded: {len(day_items)} sessions, "
                        f"{total_minutes} minutes."
                    ),
                    day_of_week=day,
                    item_ids=[i.id for i in day_items],
                )
            )
    return issues


def detect_gaps(items: list[WeeklyPlanItemView]) -> list[WeeklyPlanIssue]:
    """Informational only, and only raised once something has been planned
    for the week -- an entirely empty week isn't a "gap", it's just unstarted.
    """
    if not items:
        return []
    scheduled_days = {i.day_of_week for i in items}
    return [
        WeeklyPlanIssue(
            category="gap",
            severity="info",
            message=f"No lessons scheduled for {day.value.capitalize()}.",
            day_of_week=day,
        )
        for day in _SCHOOL_WEEKDAYS
        if day not in scheduled_days
    ]


def detect_repeated_topics(items: list[WeeklyPlanItemView]) -> list[WeeklyPlanIssue]:
    by_topic: dict[str, list[WeeklyPlanItemView]] = defaultdict(list)
    for item in items:
        if item.topic:
            by_topic[item.topic.strip().lower()].append(item)

    issues = []
    for topic, matching in by_topic.items():
        if len(matching) > 1:
            issues.append(
                WeeklyPlanIssue(
                    category="repeated_topic",
                    severity="info",
                    message=f"\"{matching[0].topic}\" is scheduled more than once this week.",
                    item_ids=[i.id for i in matching],
                )
            )
    return issues


def detect_missing_assessment(items: list[WeeklyPlanItemView]) -> list[WeeklyPlanIssue]:
    by_class: dict = defaultdict(list)
    for item in items:
        by_class[item.class_id].append(item)

    issues = []
    for class_id, class_items in by_class.items():
        if len(class_items) < _MIN_SESSIONS_BEFORE_ASSESSMENT_NUDGE:
            continue
        has_assessment = any(i.template_type == "assessment" for i in class_items)
        if not has_assessment:
            issues.append(
                WeeklyPlanIssue(
                    category="missing_assessment",
                    severity="info",
                    message=(
                        f"{class_items[0].class_name} has {len(class_items)} sessions this week "
                        "with no assessment -- worth checking understanding before moving on."
                    ),
                    item_ids=[i.id for i in class_items],
                )
            )
    return issues


def analyze_week(items: list[WeeklyPlanItemView]) -> list[WeeklyPlanIssue]:
    return [
        *detect_time_conflicts(items),
        *detect_overload(items),
        *detect_gaps(items),
        *detect_repeated_topics(items),
        *detect_missing_assessment(items),
    ]
