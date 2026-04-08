"""Harness type contracts. Every baseline and query set speaks these.

This module is the leaf — no behavior, no dependencies on other harness
modules. Imported by everything; imports nothing from harness/.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, Field

QuerySetName = Literal["freshqa", "browsecomp"]
BaselineId = Literal["b0_naive", "b1_crawl4ai", "b2_firecrawl", "b3_smart", "b4_langextract"]


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
# Baseline contract
# ---------------------------------------------------------------------------


class RetrievedContext(BaseModel):
    """What a baseline returns: the LLM-ready context for one query.

    The cost axis is measured against `text` (the only thing the answer
    LLM sees). `sources` is for auditing only and not counted in noise.
    """

    text: str
    sources: list[str] = Field(default_factory=list)
    fetched_at: datetime
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class Baseline(Protocol):
    """The contract every baseline implements. One method, async."""

    id: BaselineId
    name: str

    async def retrieve(self, query: BenchmarkQuery) -> RetrievedContext: ...


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
    query_set: QuerySetName
    query_set_version: str
    n: int
    started_at: datetime
    finished_at: datetime
    baselines: list[BaselineSummary]
    per_query_scores: list[QueryScore]  # filtered for redact_in_results
    win_loss_matrix: dict[str, dict[str, Literal["win", "loss", "tie"]]]
