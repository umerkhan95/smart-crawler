"""The two metrics. Pure functions, no I/O.

- noise_ratio: 1 - (answer_span_tokens / context_tokens)
- answer_accuracy: exact match against answer + aliases; LLM judge fallback
                   lives in judge.py and is called from runner.py.

Tokenization is fixed: tiktoken cl100k_base. The tokenizer choice is part
of the methodology — do not change without bumping the methodology version
in benchmark/methodology.md.
"""

from __future__ import annotations

from benchmark.harness.types import BenchmarkQuery, QueryScore, RetrievedContext


def count_tokens(text: str) -> int:
    """tiktoken cl100k_base token count. The single source of truth."""
    raise NotImplementedError("metrics.count_tokens — Phase 2 stub")


def find_answer_span(text: str, answer: str, aliases: list[str]) -> tuple[int, int] | None:
    """Return (start_char, end_char) of the minimum span containing the
    answer (or any alias) in text. None if not present.

    Span finding is on characters; tokens are derived by re-tokenizing the
    span. This avoids tokenizer-boundary edge cases biasing one baseline.
    """
    raise NotImplementedError("metrics.find_answer_span — Phase 2 stub")


def noise_ratio(context: RetrievedContext, query: BenchmarkQuery) -> tuple[float | None, int, int | None]:
    """Compute (noise_ratio, context_tokens, answer_span_tokens).

    Returns None for noise_ratio when the answer is not present in
    context — that query counts toward accuracy = 0 only.
    """
    raise NotImplementedError("metrics.noise_ratio — Phase 2 stub")


def exact_match_accuracy(context: RetrievedContext, query: BenchmarkQuery) -> bool:
    """First-pass accuracy check. The judge is only called when this fails."""
    raise NotImplementedError("metrics.exact_match_accuracy — Phase 2 stub")


def score_query(
    context: RetrievedContext,
    query: BenchmarkQuery,
    baseline_id: str,
    judge_used: bool,
    accuracy: int,
) -> QueryScore:
    """Assemble a QueryScore from a context, query, and accuracy result."""
    raise NotImplementedError("metrics.score_query — Phase 2 stub")
