"""Deterministic full-timetable generation via Google OR-Tools CP-SAT --
never AI, for the same reason app/planning/substitution_optimizer.py isn't:
building a weekly schedule from teachers/subjects/classes/rooms is a
constraint-satisfaction problem with a checkable, explainable answer, not
something to hand to a language model. A school admin sets up classes,
subjects, teacher qualifications and how many periods per week each class
needs of each subject; this module fills in the rest of the grid.

Pure module -- no DB, no HTTP -- so it's directly unit-testable (see
tests/test_timetable_generation.py). Room assignment is deliberately left
out of the CP-SAT model and handled by a simple greedy pass in the caller
(app/services/timetable_service.py): rooms are the least constrained
resource in a small school, and modelling them here would blow up the
variable count for little benefit -- a lesson with no room available is
still scheduled, just without one (TimetableEntry.room_id is optional).

Hard constraints (structural, never violated):
- A class is never double-booked in the same slot.
- A teacher is never double-booked in the same slot.
- A teacher only appears against a requirement they're qualified for and
  not marked unavailable for that slot -- callers must never pass a
  (requirement, slot, teacher) combination that violates this; this module
  has no way to check qualifications/availability itself.
- The same (class, subject) requirement is scheduled at most once per day,
  so a subject's periods are spread across the week rather than clustered.

Soft: none needed for a first version -- the objective simply maximises
total periods scheduled (coverage first, matching the substitution
optimizer's philosophy: fill everything that can be filled, and report the
shortfall for what can't, never invent an impossible assignment).
"""

from collections import defaultdict
from dataclasses import dataclass

from ortools.sat.python import cp_model


@dataclass(frozen=True)
class Requirement:
    id: str
    class_id: str
    subject_id: str
    periods_per_week: int


@dataclass(frozen=True)
class TimetableSlot:
    id: str
    day_of_week: int


@dataclass(frozen=True)
class ScheduledLesson:
    requirement_id: str
    class_id: str
    subject_id: str
    time_slot_id: str
    teacher_user_id: str


@dataclass(frozen=True)
class GenerationResult:
    lessons: list[ScheduledLesson]
    requested_periods: dict[str, int]
    scheduled_periods: dict[str, int]


def generate_timetable(
    requirements: list[Requirement],
    slots: list[TimetableSlot],
    qualified_teachers_by_subject: dict[str, list[str]],
    unavailable_slot_ids_by_teacher: dict[str, set[str]],
) -> GenerationResult:
    requested_periods = {r.id: r.periods_per_week for r in requirements}
    if not requirements or not slots:
        return GenerationResult(lessons=[], requested_periods=requested_periods, scheduled_periods={r.id: 0 for r in requirements})

    slot_day = {s.id: s.day_of_week for s in slots}
    model = cp_model.CpModel()

    # x[requirement_id, slot_id, teacher_id] -- only created for a teacher
    # actually qualified for that requirement's subject and available at
    # that slot, so an infeasible assignment simply has no variable at all.
    x: dict[tuple[str, str, str], cp_model.IntVar] = {}
    for req in requirements:
        for teacher_id in qualified_teachers_by_subject.get(req.subject_id, []):
            unavailable = unavailable_slot_ids_by_teacher.get(teacher_id, set())
            for slot in slots:
                if slot.id in unavailable:
                    continue
                x[(req.id, slot.id, teacher_id)] = model.new_bool_var(f"x_{req.id}_{slot.id}_{teacher_id}")

    # Each requirement scheduled at most `periods_per_week` times overall.
    scheduled_count: dict[str, cp_model.IntVar] = {}
    for req in requirements:
        req_vars = [v for (rid, _, _), v in x.items() if rid == req.id]
        count = model.new_int_var(0, req.periods_per_week, f"count_{req.id}")
        model.add(count == sum(req_vars)) if req_vars else model.add(count == 0)
        scheduled_count[req.id] = count

    # At most one lesson per (requirement, day) -- spreads periods across
    # the week instead of clustering them on one day.
    for req in requirements:
        vars_by_day: dict[int, list[cp_model.IntVar]] = defaultdict(list)
        for (rid, slot_id, _), var in x.items():
            if rid == req.id:
                vars_by_day[slot_day[slot_id]].append(var)
        for day_vars in vars_by_day.values():
            if len(day_vars) > 1:
                model.add_at_most_one(day_vars)

    # A class is never double-booked in the same slot.
    class_slot_vars: dict[tuple[str, str], list[cp_model.IntVar]] = defaultdict(list)
    req_by_id = {r.id: r for r in requirements}
    for (rid, slot_id, _), var in x.items():
        class_slot_vars[(req_by_id[rid].class_id, slot_id)].append(var)
    for var_list in class_slot_vars.values():
        if len(var_list) > 1:
            model.add_at_most_one(var_list)

    # A teacher is never double-booked in the same slot.
    teacher_slot_vars: dict[tuple[str, str], list[cp_model.IntVar]] = defaultdict(list)
    for (_, slot_id, teacher_id), var in x.items():
        teacher_slot_vars[(teacher_id, slot_id)].append(var)
    for var_list in teacher_slot_vars.values():
        if len(var_list) > 1:
            model.add_at_most_one(var_list)

    if x:
        model.maximize(sum(x.values()))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    status = solver.solve(model)

    lessons: list[ScheduledLesson] = []
    scheduled_periods = {req.id: 0 for req in requirements}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for (rid, slot_id, teacher_id), var in x.items():
            if solver.value(var) == 1:
                req = req_by_id[rid]
                lessons.append(
                    ScheduledLesson(
                        requirement_id=rid, class_id=req.class_id, subject_id=req.subject_id, time_slot_id=slot_id, teacher_user_id=teacher_id
                    )
                )
                scheduled_periods[rid] += 1

    return GenerationResult(lessons=lessons, requested_periods=requested_periods, scheduled_periods=scheduled_periods)
