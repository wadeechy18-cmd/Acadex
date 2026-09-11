from app.planning.worksheet_builder import build_answer_key, estimate_minutes, total_marks
from app.schemas.worksheet import PracticeItem, PracticeSetContent


def test_total_marks_sums_item_marks():
    content = PracticeSetContent(items=[
        PracticeItem(id="1", group="Core", prompt="Q1", marks=3, answer="A1"),
        PracticeItem(id="2", group="Challenge", prompt="Q2", marks=7, answer="A2"),
    ])
    assert total_marks(content) == 10


def test_total_marks_is_zero_for_empty_content():
    assert total_marks(PracticeSetContent()) == 0


def test_estimate_minutes_scales_with_marks():
    content = PracticeSetContent(items=[PracticeItem(id="1", group="Core", prompt="Q1", marks=10, answer="A1")])
    assert estimate_minutes(content) == 15  # 10 marks * 1.5 minutes/mark


def test_build_answer_key_mirrors_items_without_persisting_separately():
    content = PracticeSetContent(items=[
        PracticeItem(id="1", group="Core", prompt="Q1", marks=3, answer="A1"),
        PracticeItem(id="2", group="Challenge", prompt="Q2", marks=7, answer="A2"),
    ])
    key = build_answer_key(content)
    assert key.total_marks == 10
    assert [e.id for e in key.entries] == ["1", "2"]
    assert [e.answer for e in key.entries] == ["A1", "A2"]
