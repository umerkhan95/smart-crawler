"""LLM-as-judge for semantic accuracy.

Only called when exact_match_accuracy() returns False. The judge prompt is
fixed and committed to source — any change requires bumping the methodology
version. Inter-rater agreement on a hand-labeled subset gates promotion of
new prompt versions (open question in methodology.md).

Judge model: gpt-4o (NOT gpt-4o-mini — quality matters here, cost does not).
Temperature: 0. Max output tokens: 5.
"""

from __future__ import annotations

JUDGE_PROMPT_VERSION = "v0-draft"

JUDGE_SYSTEM_PROMPT = """You are an answer-equivalence judge. You will be
given a question, a ground-truth answer, and a candidate answer extracted
from a model's response. Decide whether the candidate is semantically
equivalent to the ground truth. Reply with exactly one word: YES or NO.
Do not explain. Do not equivocate."""


async def judge_equivalence(
    question: str,
    ground_truth: str,
    candidate: str,
) -> bool:
    """Single yes/no judgment. The only LLM call in the metrics layer."""
    raise NotImplementedError("judge.judge_equivalence — Phase 2 stub")
