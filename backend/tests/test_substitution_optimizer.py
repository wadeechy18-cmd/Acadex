from app.planning.substitution_optimizer import CoverCandidate, LessonToCover, optimize_substitutions


def _candidate(teacher_id: str, qualified: bool = True, workload: int = 0, recent_cover: int = 0) -> CoverCandidate:
    return CoverCandidate(teacher_user_id=teacher_id, is_qualified=qualified, workload_today=workload, recent_cover_count=recent_cover)


def test_no_lessons_returns_no_results():
    assert optimize_substitutions([], {}) == []


def test_a_lesson_with_no_candidates_is_unfilled_with_a_reason():
    lesson = LessonToCover(affected_lesson_id="L1", time_slot_id="S1")
    results = optimize_substitutions([lesson], {"L1": []})
    assert len(results) == 1
    assert results[0].teacher_user_id is None
    assert results[0].unfilled_reason is not None


def test_a_lesson_with_one_candidate_is_assigned_to_them():
    lesson = LessonToCover(affected_lesson_id="L1", time_slot_id="S1")
    results = optimize_substitutions([lesson], {"L1": [_candidate("T1")]})
    assert results[0].teacher_user_id == "T1"
    assert results[0].unfilled_reason is None


def test_prefers_a_qualified_candidate_over_an_unqualified_one():
    lesson = LessonToCover(affected_lesson_id="L1", time_slot_id="S1")
    candidates = {"L1": [_candidate("Unqualified", qualified=False), _candidate("Qualified", qualified=True)]}
    results = optimize_substitutions([lesson], candidates)
    assert results[0].teacher_user_id == "Qualified"


def test_prefers_lower_workload_candidate_for_balance():
    lesson = LessonToCover(affected_lesson_id="L1", time_slot_id="S1")
    candidates = {"L1": [_candidate("Busy", workload=5), _candidate("Free", workload=0)]}
    results = optimize_substitutions([lesson], candidates)
    assert results[0].teacher_user_id == "Free"


def test_prefers_a_candidate_who_has_not_recently_covered():
    lesson = LessonToCover(affected_lesson_id="L1", time_slot_id="S1")
    candidates = {"L1": [_candidate("FrequentCover", recent_cover=3), _candidate("RareCover", recent_cover=0)]}
    results = optimize_substitutions([lesson], candidates)
    assert results[0].teacher_user_id == "RareCover"


def test_never_assigns_the_same_teacher_to_two_lessons_at_the_same_time_slot():
    lessons = [
        LessonToCover(affected_lesson_id="L1", time_slot_id="S1"),
        LessonToCover(affected_lesson_id="L2", time_slot_id="S1"),  # same slot as L1
    ]
    # Only one teacher available for both -- it must cover just one, not both.
    candidates = {"L1": [_candidate("T1")], "L2": [_candidate("T1")]}
    results = optimize_substitutions(lessons, candidates)
    assigned = [r for r in results if r.teacher_user_id == "T1"]
    assert len(assigned) == 1
    unfilled = [r for r in results if r.teacher_user_id is None]
    assert len(unfilled) == 1


def test_fills_as_many_lessons_as_possible_even_at_a_quality_cost():
    """A single low-quality candidate can cover only one of two lessons in
    the same slot; the solver must still fill the other from whoever it
    can, rather than leaving both unfilled to "protect" the busy teacher
    for a lesson that never gets covered anyway.
    """
    lessons = [
        LessonToCover(affected_lesson_id="L1", time_slot_id="S1"),
        LessonToCover(affected_lesson_id="L2", time_slot_id="S2"),
    ]
    candidates = {
        "L1": [_candidate("OnlyOption", qualified=False, workload=10)],
        "L2": [_candidate("OnlyOption", qualified=False, workload=10)],
    }
    results = optimize_substitutions(lessons, candidates)
    assigned_count = sum(1 for r in results if r.teacher_user_id is not None)
    assert assigned_count == 2  # different time slots -- same teacher can cover both


def test_maximizes_total_lessons_filled_across_a_larger_batch():
    lessons = [LessonToCover(affected_lesson_id=f"L{i}", time_slot_id="S1") for i in range(3)]
    # Three lessons at the same slot, only two distinct teachers available across all of them.
    candidates = {
        "L0": [_candidate("A"), _candidate("B")],
        "L1": [_candidate("A"), _candidate("B")],
        "L2": [_candidate("A"), _candidate("B")],
    }
    results = optimize_substitutions(lessons, candidates)
    filled = [r for r in results if r.teacher_user_id is not None]
    assert len(filled) == 2  # at most one lesson per teacher per slot -- can never exceed 2
    assert len({r.teacher_user_id for r in filled}) == 2
