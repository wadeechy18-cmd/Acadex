from app.models.planner_class import YearGroup
from app.planning.curriculum_pack import get_pack_info, list_packs, render_pack_text


def test_list_packs_returns_all_three():
    packs = list_packs()
    assert {p.id for p in packs} == {"eyfs", "ks1_y1", "ks1_y2"}


def test_pack_year_groups_are_correct():
    assert get_pack_info("eyfs").year_group == YearGroup.RECEPTION
    assert get_pack_info("ks1_y1").year_group == YearGroup.YEAR_1
    assert get_pack_info("ks1_y2").year_group == YearGroup.YEAR_2


def test_render_pack_text_includes_objectives_and_weeks():
    text, framework_ref = render_pack_text("eyfs")
    assert "CURRICULUM OBJECTIVES" in text
    assert "=== Week 1:" in text
    assert framework_ref  # non-empty for the two packs whose year map includes it


def test_render_pack_text_handles_a_year_map_missing_the_stage_block():
    """ks1_y2's year map has no "stage" key (only "terms") -- must not crash."""
    text, framework_ref = render_pack_text("ks1_y2")
    assert "=== Week 1:" in text
    assert framework_ref == ""


def test_render_pack_text_raises_for_unknown_pack():
    import pytest

    with pytest.raises(ValueError):
        render_pack_text("ks2")


def test_all_weeks_render_without_a_missing_week_crashing():
    """EYFS's source data skips weeks 31 and 32 -- rendering must tolerate
    the gap rather than assuming a contiguous 1..38 sequence.
    """
    text, _ = render_pack_text("eyfs")
    assert "=== Week 30:" in text
    assert "=== Week 33:" in text
