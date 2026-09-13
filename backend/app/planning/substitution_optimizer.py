"""Deterministic cover-teacher assignment via Google OR-Tools CP-SAT.
Never AI: the brief is explicit that this calculation must be pure,
explainable constraint solving, not a language model guess. This module
takes plain data in and plain data out -- no DB session, no HTTP -- so it
can be unit-tested directly against the solver (see
tests/test_substitution_optimizer.py) without going through the API.

Hard constraints (enforced structurally, never violated):
- A lesson is assigned to at most one candidate.
- A candidate assigned to one lesson at a given time slot can't also be
  assigned to a different lesson at that same time slot in this batch.
Both are built into the model itself, not just scored preferences, so
the solver cannot produce a solution that breaks them.

Callers are responsible for building each lesson's candidate list so it
already excludes the absent teacher, anyone unavailable at that slot,
and anyone with a genuine timetable conflict at that slot -- those are
hard constraints this module has no way to check itself (it doesn't
know the timetable), so they must never appear as a candidate at all.

Soft constraints (the brief's preferences) are folded into a score per
candidate; the objective weights *filling a lesson at all* far above any
score difference, so the solver always maximises coverage first and
quality second -- it will use a lower-scoring candidate rather than
leave a lesson unfilled if that candidate is the only option.
"""

from dataclasses import dataclass

from ortools.sat.python import cp_model

_FILL_BONUS = 1_000
_QUALIFIED_BONUS = 50
_WORKLOAD_PENALTY_PER_LESSON = 5
_RECENT_COVER_PENALTY_PER_TIME = 10


@dataclass(frozen=True)
class CoverCandidate:
    teacher_user_id: str
    is_qualified: bool
    workload_today: int  # how many lessons this teacher already teaches today, before covering
    recent_cover_count: int  # how many times they've covered recently -- avoid repeat cover assignments


@dataclass(frozen=True)
class LessonToCover:
    affected_lesson_id: str
    time_slot_id: str


@dataclass(frozen=True)
class SubstitutionResult:
    affected_lesson_id: str
    teacher_user_id: str | None
    unfilled_reason: str | None


def _score(candidate: CoverCandidate) -> int:
    score = _QUALIFIED_BONUS if candidate.is_qualified else 0
    score -= candidate.workload_today * _WORKLOAD_PENALTY_PER_LESSON
    score -= candidate.recent_cover_count * _RECENT_COVER_PENALTY_PER_TIME
    return score


def optimize_substitutions(
    lessons: list[LessonToCover], candidates_by_lesson: dict[str, list[CoverCandidate]]
) -> list[SubstitutionResult]:
    if not lessons:
        return []

    model = cp_model.CpModel()
    assignment_vars: dict[tuple[str, str], cp_model.IntVar] = {}

    for lesson in lessons:
        for candidate in candidates_by_lesson.get(lesson.affected_lesson_id, []):
            key = (lesson.affected_lesson_id, candidate.teacher_user_id)
            assignment_vars[key] = model.new_bool_var(f"assign_{lesson.affected_lesson_id}_{candidate.teacher_user_id}")

    for lesson in lessons:
        lesson_vars = [assignment_vars[(lesson.affected_lesson_id, c.teacher_user_id)] for c in candidates_by_lesson.get(lesson.affected_lesson_id, [])]
        if lesson_vars:
            model.add_at_most_one(lesson_vars)

    teacher_slot_vars: dict[tuple[str, str], list[cp_model.IntVar]] = {}
    for lesson in lessons:
        for candidate in candidates_by_lesson.get(lesson.affected_lesson_id, []):
            key = (candidate.teacher_user_id, lesson.time_slot_id)
            teacher_slot_vars.setdefault(key, []).append(assignment_vars[(lesson.affected_lesson_id, candidate.teacher_user_id)])
    for var_list in teacher_slot_vars.values():
        if len(var_list) > 1:
            model.add_at_most_one(var_list)

    objective_terms = [
        (_FILL_BONUS + _score(candidate)) * assignment_vars[(lesson.affected_lesson_id, candidate.teacher_user_id)]
        for lesson in lessons
        for candidate in candidates_by_lesson.get(lesson.affected_lesson_id, [])
    ]
    if objective_terms:
        model.maximize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    status = solver.solve(model)

    results: list[SubstitutionResult] = []
    for lesson in lessons:
        assigned_teacher: str | None = None
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            for candidate in candidates_by_lesson.get(lesson.affected_lesson_id, []):
                var = assignment_vars.get((lesson.affected_lesson_id, candidate.teacher_user_id))
                if var is not None and solver.value(var) == 1:
                    assigned_teacher = candidate.teacher_user_id
                    break

        if assigned_teacher:
            results.append(SubstitutionResult(lesson.affected_lesson_id, assigned_teacher, None))
        elif not candidates_by_lesson.get(lesson.affected_lesson_id):
            results.append(
                SubstitutionResult(
                    lesson.affected_lesson_id,
                    None,
                    "No teacher was available and free of conflicts for this lesson.",
                )
            )
        else:
            results.append(
                SubstitutionResult(
                    lesson.affected_lesson_id,
                    None,
                    "Every available candidate was already needed for another lesson at the same time.",
                )
            )
    return results
