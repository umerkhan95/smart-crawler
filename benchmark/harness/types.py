"""Harness type contracts. Every baseline and query set speaks these.

This module is the leaf — no behavior, no dependencies on other harness
modules. Imported by everything; imports nothing from harness/.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

QuerySetName = Literal["freshqa", "browsecomp"]
BaselineId = Literal["b0_naive", "b1_crawl4ai", "b2_firecrawl", "b3_smart", "b4_langextract", "b5_tavily"]
BenchmarkMode = Literal["controlled", "e2e"]


# ---------------------------------------------------------------------------
# Query sets
# ---------------------------------------------------------------------------


class BenchmarkQuery(BaseModel):
    """One question with a ground-truth answer span."""

    qid: str
    question: str
    answer: str
    answer_aliases: list[str] = Field(default_factory=list)
    category: str | None = None
    source: QuerySetName
    redact_in_results: bool = False  # True for BrowseComp


# ---------------------------------------------------------------------------
# Retrieved context (structured chunks — Shape B)
# ---------------------------------------------------------------------------


class RetrievedChunk(BaseModel):
    """One piece of retrieved content with its source.

    Baselines return a list of these. The harness serializes them into a
    fixed template for the answer LLM (see serializer.py). Baselines do
    NOT control the final prompt format — that's the fairness guarantee.

    Fields are minimal by design (matches RAGAS list[str] + LlamaIndex
    TextNode patterns from the field). Grow only when a metric demands it.
    """

    text: str
    source_url: str
    quote: str | None = None  # verbatim span from the source, if grounded
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievedContext(BaseModel):
    """What a baseline returns for one query.

    Structured chunks, not a flat blob. The harness serializes these via a
    fixed template (serializer.py) — the serialized form is what the answer
    LLM sees and what noise_ratio is computed over. This ensures every
    baseline is measured on the same prompt format.

    B0 (naive) returns [one big chunk]. smart-crawler returns [many small
    grounded chunks]. Both go through the same serializer. Fair.
    """

    chunks: list[RetrievedChunk]
    fetched_at: datetime
    bytes_fetched: int = 0  # raw network bytes; recorded, not a primary metric
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Baseline contract
# ---------------------------------------------------------------------------


class Baseline(Protocol):
    """The contract every baseline implements. One method, async.

    In 'controlled' mode: baseline receives shared_urls and MUST use only
    those URLs (no independent discovery). Tests processing quality only.

    In 'e2e' mode: baseline discovers URLs independently from the query.
    Tests the full pipeline. shared_urls is None.
    """

    id: BaselineId
    name: str

    async def retrieve(
        self,
        query: BenchmarkQuery,
        shared_urls: list[str] | None = None,
    ) -> RetrievedContext: ...


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class QueryScore(BaseModel):
    """Per-query score. Aggregated into RunResult."""

    qid: str
    baseline_id: BaselineId
    noise_ratio: float | None = Field(ge=0.0, le=1.0)  # None if answer absent
    answer_accuracy: int = Field(ge=0, le=1)  # 0 or 1
    context_tokens: int
    answer_span_tokens: int | None
    chunks_returned: int
    bytes_fetched: int
    judge_used: bool
    redacted: bool  # True if from a restricted query set


class BaselineSummary(BaseModel):
    """Aggregate scores for one baseline on one query set."""

    baseline_id: BaselineId
    query_set: QuerySetName
    n: int
    noise_ratio_mean: float
    noise_ratio_ci95: tuple[float, float]
    answer_accuracy_mean: float
    answer_accuracy_ci95: tuple[float, float]


class RunResult(BaseModel):
    """One full benchmark run. Committed to results/ as JSON."""

    git_sha: str
    lockfile_hash: str
    answer_model: str
    judge_model: str
    seed: int
    mode: BenchmarkMode
    query_set: QuerySetName
    query_set_version: str
    n: int
    started_at: datetime
    finished_at: datetime
    baselines: list[BaselineSummary]
    per_query_scores: list[QueryScore]  # filtered for redact_in_results
    win_loss_matrix: dict[str, dict[str, Literal["win", "loss", "tie"]]]
