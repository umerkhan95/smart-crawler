"""The runner. Composes baseline + query set + metrics into a RunResult.

This is the only module in benchmark/harness/ that imports its siblings.
Modules below the runner do not import each other (same SRP rule as
smart_crawler/).

Responsibilities:
- Load a query set (with redaction flag set per BrowseComp)
- In 'controlled' mode: discover shared URLs once, pass to every baseline
- In 'e2e' mode: each baseline discovers independently (shared_urls=None)
- For each query: call baseline.retrieve(), score it via metrics + judge
- Aggregate per-baseline summaries with bootstrap 95% CI
- Build the win/loss matrix
- Redact per-query scores before serialization if redact_in_results=True
- Write the RunResult to results/<date>/<run-id>.json with full metadata
"""

from __future__ import annotations

from benchmark.harness import judge as judge
from benchmark.harness import metrics as metrics
from benchmark.harness import serializer as serializer
from benchmark.harness.types import (
    Baseline,
    BaselineSummary,
    BenchmarkMode,
    BenchmarkQuery,
    QueryScore,
    QuerySetName,
    RunResult,
)


# ---------------------------------------------------------------------------
# Controlled-mode URL discovery
# ---------------------------------------------------------------------------


async def discover_shared_urls(query: BenchmarkQuery) -> list[str]:
    """Discover URLs once per query for controlled mode.

    Uses a neutral search (not tied to any baseline) so no baseline gets
    a discovery advantage. The URLs returned here are passed to every
    baseline's retrieve(query, shared_urls=urls).
    """
    raise NotImplementedError("runner.discover_shared_urls — Phase 2 stub")


# ---------------------------------------------------------------------------
# Per-baseline evaluation
# ---------------------------------------------------------------------------


async def evaluate_query(
    baseline: Baseline,
    query: BenchmarkQuery,
    shared_urls: list[str] | None,
    answer_model: str,
    judge_model: str,
) -> QueryScore:
    """Run one baseline on one query. Returns a scored result.

    Steps:
    1. baseline.retrieve(query, shared_urls) -> RetrievedContext
    2. serializer.build_answer_prompt(ctx, query) -> prompt
    3. Call answer_model with prompt -> candidate answer
    4. metrics.exact_match_accuracy first; if fails, judge.judge_equivalence
    5. metrics.score_query assembles the QueryScore
    """
    raise NotImplementedError("runner.evaluate_query — Phase 2 stub")


async def run_baseline(
    baseline: Baseline,
    queries: list[BenchmarkQuery],
    shared_urls_per_query: dict[str, list[str]] | None,
    answer_model: str,
    judge_model: str,
) -> list[QueryScore]:
    """Run one baseline against all queries. Returns list[QueryScore]."""
    raise NotImplementedError("runner.run_baseline — Phase 2 stub")


# ---------------------------------------------------------------------------
# Aggregation + statistical reporting
# ---------------------------------------------------------------------------


def aggregate(
    scores: list[QueryScore],
    query_set: QuerySetName,
) -> BaselineSummary:
    """Bootstrap 95% CI over per-query scores. 10k resamples.

    Reports noise_ratio mean+CI and answer_accuracy mean+CI.
    """
    raise NotImplementedError("runner.aggregate — Phase 2 stub")


def build_win_loss_matrix(
    summaries: list[BaselineSummary],
) -> dict[str, dict[str, str]]:
    """Pairwise paired-test comparisons.

    A baseline wins iff:
      noise_ratio(A) < noise_ratio(B)
      AND answer_accuracy(A) >= answer_accuracy(B) - epsilon (0.02)

    Returns {baseline_id: {other_id: "win"|"loss"|"tie"}}.
    """
    raise NotImplementedError("runner.build_win_loss_matrix — Phase 2 stub")


# ---------------------------------------------------------------------------
# Redaction (BrowseComp redistribution restriction)
# ---------------------------------------------------------------------------


def redact_for_publication(result: RunResult) -> RunResult:
    """Strip per-query traces for any query with redact_in_results=True.

    This is the BrowseComp redistribution-restriction enforcement point.
    The harness MUST call this before any RunResult is committed to
    results/. A pre-commit hook also runs this as defense in depth.

    Redacted RunResult retains aggregate summaries and win/loss matrix
    but replaces per-query scores for restricted queries with a stub
    containing only qid, baseline_id, and redacted=True.
    """
    raise NotImplementedError("runner.redact_for_publication — Phase 2 stub")


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


async def run(
    baselines: list[Baseline],
    query_set: QuerySetName,
    mode: BenchmarkMode = "controlled",
    answer_model: str = "gpt-4o-mini",
    judge_model: str = "gpt-4o",
    n: int | None = None,
    seed: int = 42,
) -> RunResult:
    """Top-level entry point. The thing CI / scripts call.

    Modes:
    - 'controlled': discover URLs once per query, pass to every baseline.
      Isolates processing quality. Answers "who processes better?"
    - 'e2e': each baseline discovers independently. Tests the full
      pipeline. Answers "who retrieves better overall?"

    answer_model and judge_model are recorded in the RunResult. No
    hardcoded model anywhere — the caller decides, the result records it.
    """
    # suppress unused-import until implementation
    _ = (judge, metrics, serializer)
    raise NotImplementedError("runner.run — Phase 2 stub")
