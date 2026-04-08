"""Public data types. Every boundary in smart-crawler speaks these.

This module has zero behavior and zero dependencies on other smart_crawler
modules. It is the leaf type module that every other module is allowed to
import. Behavior modules MUST NOT import each other; they may only import
from here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Mode = Literal["structured", "summary"]
ExtractedBy = Literal["deterministic", "llm_fallback"]
RouteBranch = Literal["snippet", "single_page", "deep_crawl", "adaptive_crawl"]
StopReason = Literal[
    "schema_satisfied",
    "budget",
    "saturation",
    "no_links",
    "error",
]


# ---------------------------------------------------------------------------
# Caller-facing input
# ---------------------------------------------------------------------------


class Budget(BaseModel):
    max_pages: int = 50
    max_llm_calls: int = 5
    max_seconds: int = 120


class Query(BaseModel):
    query: str
    mode: Mode = "structured"
    schema_hint: dict[str, Any] | None = None
    seed_urls: list[str] = Field(default_factory=list)
    freshness: str | None = None  # e.g. "7d", "24h"
    budget: Budget = Field(default_factory=Budget)
    must_cite: bool = True


# ---------------------------------------------------------------------------
# Routing (L1)
# ---------------------------------------------------------------------------


class RouteDecision(BaseModel):
    """Output of router.py — how much effort this query deserves."""

    branch: RouteBranch
    rationale: str
    suggested_budget: Budget


# ---------------------------------------------------------------------------
# Fetched + filtered pages (L3, L4)
# ---------------------------------------------------------------------------


class RawPage(BaseModel):
    """A page after L3 fetch + L4 filter, ready for extraction."""

    url: str
    html: str
    fit_markdown: str
    fetched_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Planning + probing (L5)
# ---------------------------------------------------------------------------


class ExtractionPlan(BaseModel):
    """Output of planner.py — the recipe for one (query, domain) pair.

    Lives only for the duration of one smart_search() call. Never persisted.
    """

    domain: str
    pydantic_model_spec: dict[str, Any]
    css_schema: dict[str, Any]
    seed_urls: list[str]
    keyword_hints: list[str]
    url_patterns: list[str]
    notes: str = ""


class ProbeReport(BaseModel):
    """Output of probe.py — does the plan actually work on one page?"""

    url: str
    fields_found: dict[str, bool]
    coverage: float = Field(ge=0.0, le=1.0)
    raw_extracted: dict[str, Any]
    error: str | None = None


# ---------------------------------------------------------------------------
# Crawling (L3 batched)
# ---------------------------------------------------------------------------


class CrawlBatch(BaseModel):
    """Output of crawler.py — pages ready for extraction."""

    pages: list[RawPage]
    pages_visited: int
    stopped_because: StopReason


# ---------------------------------------------------------------------------
# Facts and provenance (L7)
# ---------------------------------------------------------------------------


class Source(BaseModel):
    url: str
    retrieved_at: datetime
    quote: str = Field(
        description="Verbatim snippet from the page that grounds the fact."
    )


class Fact(BaseModel):
    """A grounded, schema-valid extraction. Cannot exist without a Source."""

    data: dict[str, Any] | str
    sources: list[Source] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    extracted_by: ExtractedBy


# ---------------------------------------------------------------------------
# Errors (loud, never silent)
# ---------------------------------------------------------------------------


class RetrievalError(BaseModel):
    """A typed failure surfaced through Result.errors. No silent empties."""

    layer: Literal[
        "intake",
        "route",
        "discover",
        "fetch",
        "filter",
        "plan",
        "extract",
        "ground",
        "repair",
    ]
    url: str | None = None
    reason: str


# ---------------------------------------------------------------------------
# Final output
# ---------------------------------------------------------------------------


class Result(BaseModel):
    query: Query
    facts: list[Fact]
    pages_crawled: int
    llm_calls: int
    stopped_because: StopReason
    errors: list[RetrievalError] = Field(default_factory=list)
