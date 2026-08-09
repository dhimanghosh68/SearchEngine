from typing import Any

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    url: str = Field(min_length=1, max_length=2048)
    description: str = Field(default="", max_length=2000)
    content: str = Field(default="")


class DocumentResponse(BaseModel):
    id: str
    title: str
    url: str
    description: str
    content: str


class SearchResult(BaseModel):
    id: str
    score: float | None
    title: str
    url: str
    description: str
    content: str
    highlight: dict[str, list[str]] = {}


class SearchResponse(BaseModel):
    query: str
    page: int
    limit: int
    total: int
    results: list[SearchResult]
