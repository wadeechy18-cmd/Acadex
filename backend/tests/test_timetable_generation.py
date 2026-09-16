from app.planning.timetable_generation import Requirement, TimetableSlot, generate_timetable


def _slots(days: int, per_day: int = 1) -> list[TimetableSlot]:
    slots = []
    for day in range(days):
        for period in range(per_day):
            slots.append(TimetableSlot(id=f"d{day}p{period}", day_of_week=day))
    return slots


def test_schedules_exactly_the_requested_periods_when_feasible():
    requirements = [Requirement(id="r1", class_id="c1", subject_id="maths", periods_per_week=3)]
    slots = _slots(days=5)
    result = generate_timetable(requirements, slots, {"maths": ["t1"]}, {})

    assert result.scheduled_periods["r1"] == 3
    assert len(result.lessons) == 3
    assert all(lesson.teacher_user_id == "t1" for lesson in result.lessons)


def test_never_double_books_a_class_in_the_same_slot():
    # Two requirements for the same class, both wanting every slot -- the
    # class can only ever have one lesson per slot regardless of demand.
    requirements = [
        Requirement(id="r1", class_id="c1", subject_id="maths", periods_per_week=5),
        Requirement(id="r2", class_id="c1", subject_id="english", periods_per_week=5),
    ]
    slots = _slots(days=5)
    result = generate_timetable(requirements, slots, {"maths": ["t1"], "english": ["t2"]}, {})

    by_slot: dict[str, int] = {}
    for lesson in result.lessons:
        by_slot[lesson.time_slot_id] = by_slot.get(lesson.time_slot_id, 0) + 1
    assert all(count <= 1 for count in by_slot.values())
    # Coverage-maximizing: 5 slots split across 2 competing requirements for
    # the same class can total at most 5 scheduled periods.
    assert sum(result.scheduled_periods.values()) <= 5


def test_never_double_books_a_teacher_in_the_same_slot():
    requirements = [
        Requirement(id="r1", class_id="c1", subject_id="maths", periods_per_week=5),
        Requirement(id="r2", class_id="c2", subject_id="maths", periods_per_week=5),
    ]
    slots = _slots(days=5)
    # Only one teacher qualified for maths -- can't teach both classes at once.
    result = generate_timetable(requirements, slots, {"maths": ["t1"]}, {})

    teacher_slot_pairs = [(lesson.teacher_user_id, lesson.time_slot_id) for lesson in result.lessons]
    assert len(teacher_slot_pairs) == len(set(teacher_slot_pairs))
    assert sum(result.scheduled_periods.values()) <= 5


def test_at_most_one_period_of_the_same_requirement_per_day():
    requirements = [Requirement(id="r1", class_id="c1", subject_id="maths", periods_per_week=3)]
    slots = _slots(days=1, per_day=5)  # 5 slots, all on Monday
    result = generate_timetable(requirements, slots, {"maths": ["t1"]}, {})

    # Even though 5 slots are available in one day, at most 1 can be used
    # for this requirement -- periods must spread across different days.
    assert result.scheduled_periods["r1"] == 1


def test_unqualified_teacher_never_appears_in_the_result():
    requirements = [Requirement(id="r1", class_id="c1", subject_id="maths", periods_per_week=2)]
    slots = _slots(days=5)
    # No teacher qualified for "maths" at all.
    result = generate_timetable(requirements, slots, {"english": ["t1"]}, {})

    assert result.lessons == []
    assert result.scheduled_periods["r1"] == 0


def test_unavailable_slots_are_never_used_for_that_teacher():
    requirements = [Requirement(id="r1", class_id="c1", subject_id="maths", periods_per_week=1)]
    slots = _slots(days=1, per_day=1)
    result = generate_timetable(requirements, slots, {"maths": ["t1"]}, {"t1": {"d0p0"}})

    assert result.lessons == []
    assert result.scheduled_periods["r1"] == 0


def test_no_requirements_or_no_slots_returns_empty_result():
    assert generate_timetable([], _slots(1), {}, {}).lessons == []
    assert generate_timetable([Requirement(id="r1", class_id="c1", subject_id="maths", periods_per_week=1)], [], {}, {}).lessons == []
