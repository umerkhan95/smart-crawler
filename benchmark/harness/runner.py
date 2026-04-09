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

import random
from datetime import datetime, timezone

import numpy as np

from benchmark.harness import judge as judge
from benchmark.harness import metrics as metrics
from benchmark.harness import serializer as serializer
from benchmark.harness import tokenizer as tokenizer
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

    Uses Tavily (neutral search, not tied to any baseline) so no baseline
    gets a discovery advantage. The URLs returned here are passed to every
    baseline's retrieve(query, shared_urls=urls).
    """
    from benchmark.harness import search as search

    return await search.search_urls(query.question, max_results=5)


# ---------------------------------------------------------------------------
# Per-query evaluation
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
    2. metrics.exact_match_accuracy first
    3. If exact match fails, call judge.judge_equivalence
    4. metrics.score_query assembles the QueryScore
    """
    ctx = await baseline.retrieve(query, shared_urls=shared_urls)

    # Accuracy: exact match first, LLM judge fallback
    if metrics.exact_match_accuracy(ctx, query):
        accuracy = 1
        judge_used = False
    else:
        # Build the answer prompt and get candidate answer from answer LLM
        prompt = serializer.build_answer_prompt(ctx, query)
        candidate = await _call_answer_llm(prompt, answer_model)

        is_equivalent = await judge.judge_equivalence(
            question=query.question,
            ground_truth=query.answer,
            candidate=candidate,
            model=judge_model,
        )
        accuracy = 1 if is_equivalent else 0
        judge_used = True

    return metrics.score_query(
        ctx=ctx,
        query=query,
        baseline_id=baseline.id,
        judge_used=judge_used,
        accuracy=accuracy,
        model=answer_model,
    )


async def _call_answer_llm(prompt: str, model: str) -> str:
    """Call the answer LLM and extract its response.

    Temperature 0, single completion. Model is configurable — passed
    from runner.run(answer_model=...).
    """
    from benchmark.harness import llm as llm

    return await llm.complete(
        prompt=prompt,
        model=model,
        temperature=0.0,
        max_tokens=256,
    )


# ---------------------------------------------------------------------------
# Per-baseline evaluation
# ---------------------------------------------------------------------------


async def run_baseline(
    baseline: Baseline,
    queries: list[BenchmarkQuery],
    shared_urls_per_query: dict[str, list[str]] | None,
    answer_model: str,
    judge_model: str,
) -> list[QueryScore]:
    """Run one baseline against all queries. Returns list[QueryScore]."""
    scores = []
    for query in queries:
        shared_urls = (
            shared_urls_per_query.get(query.qid) if shared_urls_per_query else None
        )
        score = await evaluate_query(
            baseline, query, shared_urls, answer_model, judge_model
        )
        scores.append(score)
    return scores


# ---------------------------------------------------------------------------
# Aggregation + statistical reporting
# ---------------------------------------------------------------------------


def aggregate(
    scores: list[QueryScore],
    baseline_id: str,
    query_set: QuerySetName,
    n_resamples: int = 10_000,
    seed: int = 42,
) -> BaselineSummary:
    """Bootstrap 95% CI over per-query scores. 10k resamples.

    Reports noise_ratio mean+CI and answer_accuracy mean+CI.
    Queries where noise_ratio is None (answer absent) are excluded from
    the noise_ratio computation but included in accuracy.
    """
    rng = np.random.default_rng(seed)

    # Accuracy: all queries
    acc_values = np.array([s.answer_accuracy for s in scores], dtype=np.float64)
    acc_mean = float(np.mean(acc_values))
    acc_ci = _bootstrap_ci(acc_values, rng, n_resamples)

    # Noise: only queries where noise_ratio is defined
    noise_values = np.array(
        [s.noise_ratio for s in scores if s.noise_ratio is not None],
        dtype=np.float64,
    )
    if len(noise_values) > 0:
        noise_mean = float(np.mean(noise_values))
        noise_ci = _bootstrap_ci(noise_values, rng, n_resamples)
    else:
        noise_mean = 0.0
        noise_ci = (0.0, 0.0)

    return BaselineSummary(
        baseline_id=baseline_id,
        query_set=query_set,
        n=len(scores),
        noise_ratio_mean=noise_mean,
        noise_ratio_ci95=noise_ci,
        answer_accuracy_mean=acc_mean,
        answer_accuracy_ci95=acc_ci,
    )


def _bootstrap_ci(
    values: np.ndarray,
    rng: np.random.Generator,
    n_resamples: int,
) -> tuple[float, float]:
    """Bootstrap 95% confidence interval (percentile method)."""
    n = len(values)
    if n == 0:
        return (0.0, 0.0)

    boot_means = np.empty(n_resamples, dtype=np.float64)
    for i in range(n_resamples):
        sample = rng.choice(values, size=n, replace=True)
        boot_means[i] = np.mean(sample)

    lower = float(np.percentile(boot_means, 2.5))
    upper = float(np.percentile(boot_means, 97.5))
    return (lower, upper)


def build_win_loss_matrix(
    all_scores: dict[str, list[QueryScore]],
    epsilon: float = 0.02,
) -> dict[str, dict[str, str]]:
    """Pairwise comparisons between baselines.

    A baseline A wins over B iff:
      mean(noise_ratio(A)) < mean(noise_ratio(B))
      AND mean(accuracy(A)) >= mean(accuracy(B)) - epsilon

    epsilon = 0.02 (within 2 percentage points). Trading accuracy for
    noise reduction is explicitly NOT a win.
    """
    baseline_ids = sorted(all_scores.keys())
    matrix: dict[str, dict[str, str]] = {}

    for a_id in baseline_ids:
        matrix[a_id] = {}
        a_scores = all_scores[a_id]
        a_noise = np.mean([s.noise_ratio for s in a_scores if s.noise_ratio is not None])
        a_acc = np.mean([s.answer_accuracy for s in a_scores])

        for b_id in baseline_ids:
            if a_id == b_id:
                matrix[a_id][b_id] = "tie"
                continue

            b_scores = all_scores[b_id]
            b_noise = np.mean([s.noise_ratio for s in b_scores if s.noise_ratio is not None])
            b_acc = np.mean([s.answer_accuracy for s in b_scores])

            if a_noise < b_noise and a_acc >= b_acc - epsilon:
                matrix[a_id][b_id] = "win"
            elif b_noise < a_noise and b_acc >= a_acc - epsilon:
                matrix[a_id][b_id] = "loss"
            else:
                matrix[a_id][b_id] = "tie"

    return matrix


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
    redacted_scores = []
    for score in result.per_query_scores:
        if score.redacted:
            redacted_scores.append(
                QueryScore(
                    qid=score.qid,
                    baseline_id=score.baseline_id,
                    noise_ratio=None,
                    answer_accuracy=0,
                    context_tokens=0,
                    answer_span_tokens=None,
                    chunks_returned=0,
                    bytes_fetched=0,
                    judge_used=False,
                    redacted=True,
                )
            )
        else:
            redacted_scores.append(score)

    return result.model_copy(update={"per_query_scores": redacted_scores})


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


async def run(
    baselines: list[Baseline],
    queries: list[BenchmarkQuery],
    mode: BenchmarkMode = "controlled",
    answer_model: str = "gpt-4o-mini",
    judge_model: str = "gpt-4o",
    query_set: QuerySetName = "freshqa",
    query_set_version: str = "latest",
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
    random.seed(seed)
    started_at = datetime.now(timezone.utc)

    # Subsample if n is specified
    if n is not None and n < len(queries):
        queries = random.sample(queries, n)

    # Controlled mode: discover shared URLs once per query
    shared_urls_per_query: dict[str, list[str]] | None = None
    if mode == "controlled":
        shared_urls_per_query = {}
        for q in queries:
            shared_urls_per_query[q.qid] = await discover_shared_urls(q)

    # Run each baseline
    all_scores: dict[str, list[QueryScore]] = {}
    summaries: list[BaselineSummary] = []
    all_per_query: list[QueryScore] = []

    for baseline in baselines:
        scores = await run_baseline(
            baseline, queries, shared_urls_per_query, answer_model, judge_model
        )
        all_scores[baseline.id] = scores
        all_per_query.extend(scores)
        summaries.append(
            aggregate(scores, baseline.id, query_set, seed=seed)
        )

    # Win/loss matrix
    matrix = build_win_loss_matrix(all_scores)

    finished_at = datetime.now(timezone.utc)

    result = RunResult(
        git_sha=_get_git_sha(),
        lockfile_hash="",  # TODO: compute from uv.lock
        answer_model=answer_model,
        judge_model=judge_model,
        seed=seed,
        mode=mode,
        query_set=query_set,
        query_set_version=query_set_version,
        n=len(queries),
        started_at=started_at,
        finished_at=finished_at,
        baselines=summaries,
        per_query_scores=all_per_query,
        win_loss_matrix=matrix,
    )

    # Redact before returning (BrowseComp enforcement)
    return redact_for_publication(result)


def _get_git_sha() -> str:
    """Get the current git SHA for reproducibility metadata."""
    import subprocess

    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
