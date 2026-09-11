"""Renders the bundled starter curriculum packs (app/curriculum_packs/) into
plain text, so they can flow through exactly the same upload_resource() ->
extract -> clean -> chunk pipeline as a teacher's own uploaded scheme of
work (see resource_service.py). Pure Python, no database access.

Each pack is a UK National Curriculum-aligned, week-by-week, day-by-day
lesson bank (EYFS Reception, or KS1 Year 1/Year 2) supplied as JSON: one
`*_year_map.json` (stage overview + subject/area objectives) plus one
`*_week<N>_lessons.json` per teaching week. The two source shapes (EYFS's
areas_of_learning/early_learning_goals/area_id/elg_ref/main_activity vs
KS1's subjects/key_objectives/subject_id/objective_ref/main_teaching_input
+independent_task) are handled generically rather than with two near-
duplicate renderers.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from app.models.planner_class import YearGroup

_PACKS_ROOT = Path(__file__).resolve().parent.parent / "curriculum_packs"

_PACK_REGISTRY: dict[str, dict] = {
    "eyfs": {
        "dir": _PACKS_ROOT / "early_years",
        "year_map_glob": "*_year_map.json",
        "year_group": YearGroup.RECEPTION,
        "display_name": "EYFS (Reception) — Full Year",
    },
    "ks1_y1": {
        "dir": _PACKS_ROOT / "ks1" / "year_1",
        "year_map_glob": "*_year_map.json",
        "year_group": YearGroup.YEAR_1,
        "display_name": "KS1 Year 1 — Full Year",
    },
    "ks1_y2": {
        "dir": _PACKS_ROOT / "ks1" / "year_2",
        "year_map_glob": "*_year_map.json",
        "year_group": YearGroup.YEAR_2,
        "display_name": "KS1 Year 2 — Full Year",
    },
}


@dataclass
class CurriculumPackInfo:
    id: str
    display_name: str
    year_group: YearGroup


def list_packs() -> list[CurriculumPackInfo]:
    return [
        CurriculumPackInfo(id=pack_id, display_name=meta["display_name"], year_group=meta["year_group"])
        for pack_id, meta in _PACK_REGISTRY.items()
    ]


def get_pack_info(pack_id: str) -> CurriculumPackInfo:
    if pack_id not in _PACK_REGISTRY:
        raise ValueError(f"Unknown curriculum pack: {pack_id}")
    meta = _PACK_REGISTRY[pack_id]
    return CurriculumPackInfo(id=pack_id, display_name=meta["display_name"], year_group=meta["year_group"])


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _render_objectives(stage: dict) -> list[str]:
    subject_key = "subjects" if "subjects" in stage else "areas_of_learning"
    goal_key = "key_objectives" if subject_key == "subjects" else "early_learning_goals"
    goal_id_key = "obj_id" if subject_key == "subjects" else "elg_id"

    lines = ["CURRICULUM OBJECTIVES"]
    for subject in stage.get(subject_key, []):
        lines.append(f"{subject['name']} ({subject['id']}):")
        for goal in subject.get(goal_key, []):
            label = goal.get("strand") or goal.get("title") or ""
            lines.append(f"  {goal[goal_id_key]} [{label}]: {goal['description']}")
    return ["\n".join(lines)]


def _render_lesson(lesson: dict) -> str:
    subject = lesson.get("subject_id") or lesson.get("area_id") or ""
    parts = [f"{lesson.get('day', '')} — {subject}: {lesson.get('title', '')}"]

    def add(label: str, value) -> None:
        if not value:
            return
        if isinstance(value, list):
            value = "; ".join(str(v) for v in value)
        parts.append(f"{label}: {value}")

    add("Learning objective", lesson.get("learning_objective"))
    add("Success criteria", lesson.get("success_criteria"))
    add("Key vocabulary", lesson.get("key_vocabulary"))
    add("Starter", lesson.get("starter_activity"))
    add("Main teaching input", lesson.get("main_teaching_input"))
    add("Main activity", lesson.get("main_activity"))
    add("Independent task", lesson.get("independent_task"))
    add("Resources needed", lesson.get("resources_needed"))
    add("Key questions", lesson.get("key_questions"))
    differentiation = lesson.get("differentiation") or {}
    add("Support", differentiation.get("support"))
    add("Greater depth / extension", differentiation.get("greater_depth") or differentiation.get("extension"))
    add("Assessment notes", lesson.get("assessment_notes"))
    add("Plenary", lesson.get("plenary"))
    add("Home link", lesson.get("home_link"))

    return "\n".join(parts)


def render_pack_text(pack_id: str) -> tuple[str, str]:
    """Returns (rendered_text, framework_ref) for the given pack."""
    meta = _PACK_REGISTRY.get(pack_id)
    if not meta:
        raise ValueError(f"Unknown curriculum pack: {pack_id}")

    pack_dir: Path = meta["dir"]
    year_map_paths = sorted(pack_dir.glob(meta["year_map_glob"]))
    if not year_map_paths:
        raise FileNotFoundError(f"No year map found for curriculum pack {pack_id} in {pack_dir}")

    # Not every supplied year map includes the "stage" metadata block (one of
    # the three source files omits it, containing only "terms") -- fall back
    # to the registry's own display name rather than crashing the import;
    # the week-by-week lesson content, the actual value here, is unaffected.
    year_map = _load_json(year_map_paths[0])
    stage = year_map.get("stage", {"name": meta["display_name"], "age_range": "", "framework_ref": ""})

    week_files = sorted(
        pack_dir.glob("*week*_lessons.json"),
        key=lambda p: _load_json(p).get("week_number", 0),
    )

    sections = [f"{stage['name']} ({stage.get('age_range', '')})\nFramework: {stage.get('framework_ref', '')}"]
    sections.extend(_render_objectives(stage))

    for week_path in week_files:
        week = _load_json(week_path)
        header = f"=== Week {week.get('week_number')}: {week.get('sub_theme', '')} ==="
        sections.append(header)
        sections.extend(_render_lesson(lesson) for lesson in week.get("lessons", []))

    return "\n\n".join(sections), stage.get("framework_ref", "")
