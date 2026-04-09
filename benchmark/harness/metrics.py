"""The two metrics. Pure functions, no I/O.

- noise_ratio: 1 - (answer_span_tokens / context_tokens)
- answer_accuracy: exact match against answer + aliases; LLM judge fallback
                   lives in judge.py and is called from runner.py.

Both metrics operate on the SERIALIZED form from serializer.py — that is,
the exact text the answer LLM sees. This ensures metrics measure what
the model actually processes, not the raw chunks.

Tokenization flows through tokenizer.py (the single source of truth).
Always tokenize the full serialized string, never sum per-chunk counts
(BPE boundary problem: 5-15% error when summing).

Answer span normalization follows SQuAD/TriviaQA conventions:
1. Lowercase
2. Remove articles (a, an, the)
3. Remove punctuation
4. Collapse whitespace
"""

from __future__ import annotations

import re
import string

from benchmark.harness.serializer import serialize_chunks
from benchmark.harness.tokenizer import count_tokens
from benchmark.harness.types import (
    BaselineId,
    BenchmarkQuery,
    QueryScore,
    RetrievedContext,
)


# ---------------------------------------------------------------------------
# Answer normalization (SQuAD/TriviaQA convention)
# ---------------------------------------------------------------------------

_ARTICLES_RE = re.compile(r"\b(a|an|the)\b", re.IGNORECASE)
_PUNCT_TABLE = str.maketrans("", "", string.punctuation)


def normalize_answer(text: str) -> str:
    """Normalize text for answer matching.

    Follows the SQuAD/TriviaQA normalization pipeline:
    1. Lowercase
    2. Remove articles (a, an, the)
    3. Remove punctuation
    4. Collapse whitespace

    Order matters for reproducibility — do not reorder.
    """
    text = text.lower()
    text = _ARTICLES_RE.sub(" ", text)
    text = text.translate(_PUNCT_TABLE)
    text = " ".join(text.split())
    return text.strip()


# ---------------------------------------------------------------------------
# Answer span finding
# ---------------------------------------------------------------------------


def find_answer_span(
    text: str,
    answer: str,
    aliases: list[str],
    model: str | None = None,
) -> tuple[int, int, int] | None:
    """Find the answer span in the serialized context.

    Returns (start_char, end_char, span_tokens) or None if the answer
    is not present.

    Strategy (following SQuAD/TriviaQA/Natural Questions practice):
    1. Try case-insensitive exact match for answer, then each alias
    2. Try normalized match (SQuAD normalization) for answer, then aliases
    3. Return None if no match found

    Span finding is on characters first, then the matched span is
    re-tokenized to get span_tokens. This avoids tokenizer-boundary
    edge cases that would bias baselines whose chunks happen to align
    with BPE merge points.
    """
    candidates = [answer] + aliases

    # Pass 1: case-insensitive exact match (most precise)
    text_lower = text.lower()
    for candidate in candidates:
        idx = text_lower.find(candidate.lower())
        if idx != -1:
            end = idx + len(candidate)
            span_text = text[idx:end]
            span_tokens = count_tokens(span_text, model=model)
            return idx, end, span_tokens

    # Pass 2: normalized match (SQuAD convention — handles punctuation,
    # articles, whitespace differences between answer and context)
    text_normalized = normalize_answer(text)
    for candidate in candidates:
        candidate_normalized = normalize_answer(candidate)
        if not candidate_normalized:
            continue
        idx = text_normalized.find(candidate_normalized)
        if idx != -1:
            # Map normalized index back to approximate original position.
            # We re-scan the original text for the best approximate match
            # by sliding a window of the candidate's length.
            approx = _find_approximate_original_span(
                text, candidate_normalized, idx
            )
            if approx is not None:
                start, end = approx
                span_text = text[start:end]
                span_tokens = count_tokens(span_text, model=model)
                return start, end, span_tokens

    return None


def _find_approximate_original_span(
    original: str,
    normalized_target: str,
    normalized_idx: int,
) -> tuple[int, int] | None:
    """Map a normalized match back to the original text.

    Uses a sliding window over the original text, normalizing each window
    and checking for a match. Window size is based on the normalized
    target length with a margin for removed characters.
    """
    target_len = len(normalized_target)
    # Search with margin since normalization removes characters
    margin = max(target_len, 20)
    # Estimate start position in original (normalized index is a lower bound)
    search_start = max(0, normalized_idx - margin)
    search_end = min(len(original), normalized_idx + target_len + margin * 2)

    best_start = None
    best_end = None

    for start in range(search_start, search_end):
        for end in range(start + 1, min(start + target_len + margin, len(original) + 1)):
            window = original[start:end]
            if normalize_answer(window) == normalized_target:
                # Prefer the tightest (shortest) match
                if best_start is None or (end - start) < (best_end - best_start):
                    best_start = start
                    best_end = end

    if best_start is not None:
        return best_start, best_end
    return None


# ---------------------------------------------------------------------------
# Core metrics
# ---------------------------------------------------------------------------


def compute_noise_ratio(
    ctx: RetrievedContext,
    query: BenchmarkQuery,
    model: str | None = None,
) -> tuple[float | None, int, int | None]:
    """Compute (noise_ratio, context_tokens, answer_span_tokens).

    Operates on serialize_chunks(ctx) — the exact text the answer LLM
    sees. This is the cost axis.

    Returns None for noise_ratio when the answer is not present in the
    serialized context — that query counts toward accuracy = 0 only.
    Returning nothing is not a way to get a low noise score.
    """
    serialized = serialize_chunks(ctx)
    context_tokens = count_tokens(serialized, model=model)

    if context_tokens == 0:
        return None, 0, None

    span = find_answer_span(
        serialized, query.answer, query.answer_aliases, model=model
    )
    if span is None:
        return None, context_tokens, None

    _start, _end, answer_span_tokens = span
    ratio = 1.0 - (answer_span_tokens / context_tokens)
    return ratio, context_tokens, answer_span_tokens


def exact_match_accuracy(
    ctx: RetrievedContext,
    query: BenchmarkQuery,
) -> bool:
    """First-pass accuracy check. The judge is only called when this fails.

    Uses normalized matching (SQuAD convention): the answer (or any alias)
    is considered present if the normalized form appears in the normalized
    serialized context.
    """
    serialized = normalize_answer(serialize_chunks(ctx))
    candidates = [normalize_answer(query.answer)] + [
        normalize_answer(a) for a in query.answer_aliases
    ]
    return any(c and c in serialized for c in candidates)


# ---------------------------------------------------------------------------
# Score assembly
# ---------------------------------------------------------------------------


def score_query(
    ctx: RetrievedContext,
    query: BenchmarkQuery,
    baseline_id: BaselineId,
    judge_used: bool,
    accuracy: int,
    model: str | None = None,
) -> QueryScore:
    """Assemble a QueryScore from a context, query, and accuracy result."""
    noise, context_tokens, span_tokens = compute_noise_ratio(
        ctx, query, model=model
    )

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
