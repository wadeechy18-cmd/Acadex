"""Deterministic helpers shared by worksheets and homework -- both use the
same PracticeSetContent shape, so one module covers both rather than
duplicating this arithmetic per model. No AI involved.
"""

from app.schemas.worksheet import AnswerKey, AnswerKeyEntry, PracticeSetContent

# A rough, fixed rate used only to give teachers a ballpark completion time
# alongside a worksheet/homework sheet -- never shown as an authoritative
# figure, just a planning aid.
_MINUTES_PER_MARK = 1.5


def total_marks(content: PracticeSetContent) -> int:
    return sum(item.marks for item in content.items)


def estimate_minutes(content: PracticeSetContent) -> int:
    return round(total_marks(content) * _MINUTES_PER_MARK)


def build_answer_key(content: PracticeSetContent) -> AnswerKey:
    return AnswerKey(
        total_marks=total_marks(content),
        entries=[
            AnswerKeyEntry(id=item.id, group=item.group, prompt=item.prompt, marks=item.marks, answer=item.answer)
            for item in content.items
        ],
    )
