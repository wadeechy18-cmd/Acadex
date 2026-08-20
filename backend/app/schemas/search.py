import uuid

from pydantic import BaseModel


class SearchResult(BaseModel):
    type: str
    id: uuid.UUID
    title: str
    subtitle: str | None
    url: str


class SearchResponse(BaseModel):
    results: list[SearchResult]
