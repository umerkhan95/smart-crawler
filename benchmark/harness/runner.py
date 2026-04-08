"""The runner. Composes baseline + query set + metrics into a RunResult.

This is the only module in benchmark/harness/ that imports its siblings.
Modules below the runner do not import each other (same SRP rule as
smart_crawler/).

Responsibilities:
- Load a query set (with redaction flag set per BrowseComp)
- For each query: call baseline.retrieve(), score it
- Aggregate per-baseline summaries with bootstrap 95% CI
- Build the win/loss matrix
- Redact per-query scores from RunResult before serialization if any
  query has redact_in_results=True
- Write the RunResult to results/<date>/<run-id>.json with full metadata
"""

from __future__ import annotations

from benchmark.harness.types import (
    Baseline,
    BenchmarkQuery,
    BaselineSummary,
    QuerySetName,
    RunResult,
)


async def run_baseline(
    baseline: Baseline,
    queries: list[BenchmarkQuery],
    seed: int,
) -> list:
    """Run one baseline against a list of queries. Returns list[QueryScore]."""
    raise NotImplementedError("runner.run_baseline — Phase 2 stub")


def aggregate(scores: list, query_set: QuerySetName) -> BaselineSummary:
    """Bootstrap 95% CI over per-query scores. 10k resamples."""
    raise NotImplementedError("runner.aggregate — Phase 2 stub")


def build_win_loss_matrix(summaries: list[BaselineSummary]) -> dict:
    """Pairwise paired-test comparisons. Returns the win/loss matrix."""
    raise NotImplementedError("runner.build_win_loss_matrix — Phase 2 stub")


def redact_for_publication(result: RunResult) -> RunResult:
    """Strip per-query traces for any query with redact_in_results=True.

    This is the BrowseComp redistribution-restriction enforcement point.
    The harness MUST call this before any RunResult is committed to
    results/. A pre-commit hook also runs this as defense in depth.
    """
    raise NotImplementedError("runner.redact_for_publication — Phase 2 stub")


async def run(
    baselines: list[Baseline],
    query_set: QuerySetName,
    n: int | None = None,
    seed: int = 42,
) -> RunResult:
    """Top-level entry point. The thing CI / scripts call."""
    raise NotImplementedError("runner.run — Phase 2 stub")
