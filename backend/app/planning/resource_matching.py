"""Resource-first retrieval: given a subject/year group/topic, rank a
teacher's own uploaded resource library and return the most relevant ones
to feed into lesson generation. Pure Python -- text-overlap scoring plus
tag matching, no AI, no network calls. This is what lets a teacher skip
manually finding "the PDF" every time: the library itself is searched
before any AI call is made, and only the handful of matched excerpts (never
the whole library) go into the generation prompt (see
app/planning/lesson_generation.py's build_resource_excerpts, which caps
total injected characters regardless of how many resources this returns).
"""

import re
import uuid

from sqlalchemy.orm import Session

from app.models.resource import ExtractionStatus, Resource

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "about", "into",
    "lesson", "class", "make", "me", "need", "teach", "teaching", "tomorrow", "today", "minute", "minutes",
}


def _tokenize(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS and len(w) > 2}


def _keyword_overlap_score(resource_tokens: set[str], query_tokens: set[str]) -> float:
    if not resource_tokens or not query_tokens:
        return 0.0
    return len(resource_tokens & query_tokens) / len(query_tokens)


# Weights: tag matches are a strong, reliable signal (a teacher deliberately
# filed this resource under this subject/year group); text overlap is a
# weaker best-effort fallback for untagged resources.
_SUBJECT_TAG_WEIGHT = 3.0
_YEAR_GROUP_TAG_WEIGHT = 2.0
_TEXT_OVERLAP_WEIGHT = 4.0

# A resource that scores below this (no tag match and negligible text
# overlap) isn't relevant enough to bother injecting -- an empty result is
# always better than diluting the prompt with unrelated material.
_MIN_RELEVANCE_SCORE = 0.5


def score_resource(
    resource: Resource,
    *,
    subject_id: uuid.UUID | None,
    year_group_id: uuid.UUID | None,
    query_tokens: set[str],
) -> float:
    score = 0.0
    if subject_id is not None and resource.subject_id == subject_id:
        score += _SUBJECT_TAG_WEIGHT
    if year_group_id is not None and resource.year_group_id == year_group_id:
        score += _YEAR_GROUP_TAG_WEIGHT

    haystack = resource.display_name
    if resource.extraction_status == ExtractionStatus.DONE and resource.extracted_text:
        haystack = f"{haystack} {resource.extracted_text}"
    score += _TEXT_OVERLAP_WEIGHT * _keyword_overlap_score(_tokenize(haystack), query_tokens)

    return score


def find_relevant_resources(
    db: Session,
    owner_user_id: uuid.UUID,
    *,
    subject_id: uuid.UUID | None,
    year_group_id: uuid.UUID | None,
    topic_title: str,
    extra_keywords: str | None = None,
    limit: int = 5,
) -> list[Resource]:
    """Best-effort search of a teacher's own resource library. Returns the
    top-scoring resources above a minimum relevance bar, most relevant
    first -- may return an empty list, which is the correct result when
    nothing in the library actually relates to this lesson.
    """
    query_text = topic_title if not extra_keywords else f"{topic_title} {extra_keywords}"
    query_tokens = _tokenize(query_text)

    resources = db.query(Resource).filter_by(owner_user_id=owner_user_id).all()
    scored = [(score_resource(r, subject_id=subject_id, year_group_id=year_group_id, query_tokens=query_tokens), r) for r in resources]
    scored = [(score, r) for score, r in scored if score >= _MIN_RELEVANCE_SCORE]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [r for _, r in scored[:limit]]
