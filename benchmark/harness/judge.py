"""LLM-as-judge for semantic accuracy.

Only called when exact_match_accuracy() returns False. The judge prompt is
fixed and committed to source — any change requires bumping the version
and re-validating inter-rater agreement on a hand-labeled subset.

Judge model is configurable (passed from runner.run). Temperature: 0.
Max output tokens: 5.
"""

from __future__ import annotations

JUDGE_PROMPT_VERSION = "v1"

JUDGE_SYSTEM_PROMPT = """You are an answer-equivalence judge. You will be given a question, a ground-truth answer, and a candidate answer extracted from a model's response. Decide whether the candidate is semantically equivalent to the ground truth. Reply with exactly one word: YES or NO. Do not explain. Do not equivocate."""


async def judge_equivalence(
    question: str,
    ground_truth: str,
    candidate: str,
    model: str = "gpt-4o",
) -> bool:
    """Single yes/no judgment. The only LLM call in the metrics layer.

    Model is configurable — passed from runner.run(judge_model=...).
    Recorded in every RunResult so judgments are reproducible.
    """
    raise NotImplementedError("judge.judge_equivalence — Phase 2 stub")
