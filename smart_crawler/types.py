"""Public data types. Every boundary in smart-crawler speaks these."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Mode = Literal["structured", "summary"]


class Budget(BaseModel):
    max_pages: int = 50
    max_llm_calls: int = 5
    max_seconds: int = 120


class Source(BaseModel):
    url: str
    retrieved_at: datetime
    quote: str = Field(
        description="Verbatim snippet from the page that grounds the fact."
    )


class Fact(BaseModel):
    data: dict[str, Any] | str
    sources: list[Source]
    confidence: float = Field(ge=0.0, le=1.0)
    extracted_by: Literal["deterministic", "llm_fallback"]


class Query(BaseModel):
    query: str
    mode: Mode = "structured"
    schema_hint: dict[str, Any] | None = None
    freshness: str | None = None  # e.g. "7d", "24h"
    budget: Budget = Field(default_factory=Budget)
    must_cite: bool = True


class Result(BaseModel):
    query: Query
    facts: list[Fact]
    pages_crawled: int
    llm_calls: int
    errors: list[str] = Field(default_factory=list)
