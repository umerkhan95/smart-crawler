"""The two metrics. Pure functions, no I/O.

- noise_ratio: 1 - (answer_span_tokens / context_tokens)
- answer_accuracy: exact match against answer + aliases; LLM judge fallback
                   lives in judge.py and is called from runner.py.

Both metrics operate on the SERIALIZED form from serializer.py — that is,
the exact text the answer LLM sees. This ensures metrics measure what
the model actually processes, not the raw chunks.

Tokenization is fixed: tiktoken cl100k_base. The tokenizer choice is part
of the methodology — do not change without bumping the methodology version
in benchmark/methodology.md.
"""

from __future__ import annotations

from benchmark.harness.serializer import serialize_chunks
from benchmark.harness.types import (
    BaselineId,
    BenchmarkQuery,
    QueryScore,
    RetrievedContext,
)


def count_tokens(text: str) -> int:
    """tiktoken cl100k_base token count. The single source of truth.

    Every token count in the benchmark flows through this function.
    No other module is allowed to tokenize.
    """
    raise NotImplementedError("metrics.count_tokens — Phase 2 stub")


def find_answer_span(
    text: str, answer: str, aliases: list[str]
) -> tuple[int, int] | None:
    """Return (start_char, end_char) of the minimum span containing the
    answer (or any alias) in text. None if not present.

    Matching is case-insensitive. Tries the primary answer first, then
    each alias in order. Returns the first match found (shortest span
    wins on ties within the same answer variant).

    Span finding is on characters; tokens are derived by re-tokenizing
    the span. This avoids tokenizer-boundary edge cases biasing one
    baseline.
    """
    raise NotImplementedError("metrics.find_answer_span — Phase 2 stub")


def compute_noise_ratio(
    ctx: RetrievedContext, query: BenchmarkQuery
) -> tuple[float | None, int, int | None]:
    """Compute (noise_ratio, context_tokens, answer_span_tokens).

    Operates on serialize_chunks(ctx) — the exact text the answer LLM
    sees. This is the cost axis.

    Returns None for noise_ratio when the answer is not present in the
    serialized context — that query counts toward accuracy = 0 only.
    Returning nothing is not a way to get a low noise score.
    """
    serialized = serialize_chunks(ctx)
    context_tokens = count_tokens(serialized)

    if context_tokens == 0:
        return None, 0, None

    span = find_answer_span(
        serialized, query.answer, query.answer_aliases
    )
    if span is None:
        return None, context_tokens, None

    answer_span_text = serialized[span[0] : span[1]]
    answer_span_tokens = count_tokens(answer_span_text)

    ratio = 1.0 - (answer_span_tokens / context_tokens)
    return ratio, context_tokens, answer_span_tokens


def exact_match_accuracy(
    ctx: RetrievedContext, query: BenchmarkQuery
) -> bool:
    """First-pass accuracy check. The judge is only called when this fails.

    Checks whether the answer (or any alias) appears verbatim in the
    serialized context. Case-insensitive.
    """
    serialized = serialize_chunks(ctx).lower()
    candidates = [query.answer.lower()] + [a.lower() for a in query.answer_aliases]
    return any(c in serialized for c in candidates)


def score_query(
    ctx: RetrievedContext,
    query: BenchmarkQuery,
    baseline_id: BaselineId,
    judge_used: bool,
    accuracy: int,
) -> QueryScore:
    """Assemble a QueryScore from a context, query, and accuracy result."""
    noise, context_tokens, span_tokens = compute_noise_ratio(ctx, query)

    return QueryScore(
        qid=query.qid,
        baseline_id=baseline_id,
        noise_ratio=noise,
        answer_accuracy=accuracy,
        context_tokens=context_tokens,
        answer_span_tokens=span_tokens,
        chunks_returned=len(ctx.chunks),
        bytes_fetched=ctx.bytes_fetched,
        judge_used=judge_used,
        redacted=query.redact_in_results,
    )
