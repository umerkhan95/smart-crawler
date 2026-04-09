"""LLM client for the smart_crawler library.

Single point of contact for all LLM calls in the library (citer, planner,
repairer). No other library module imports openai directly.

Also provides an NLI entailment check via LLM — used by citer as Tier 2
verification when string matching fails.
"""

from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI, APIError, RateLimitError

load_dotenv()

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not set. Add it to .env or export it."
            )
        _client = AsyncOpenAI(api_key=api_key)
    return _client


async def complete(
    prompt: str,
    model: str = "gpt-4o-mini",
    system: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> str:
    """Single completion call with retry on rate limits.

    Returns the assistant's text content. Empty string on empty choices
    (content filter refusals).
    """
    client = _get_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for attempt in range(3):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if not response.choices:
                logger.error("OpenAI returned empty choices for model=%s", model)
                return ""
            return response.choices[0].message.content or ""
        except RateLimitError:
            wait = 2 ** attempt
            logger.warning("Rate limited (attempt %d/3), retrying in %ds", attempt + 1, wait)
            await asyncio.sleep(wait)
        except APIError as exc:
            logger.error("OpenAI API error (attempt %d/3): %s", attempt + 1, exc)
            if attempt == 2:
                raise

    return ""


# ---------------------------------------------------------------------------
# NLI entailment check via LLM (Tier 2 verification)
# ---------------------------------------------------------------------------

_NLI_SYSTEM = """You are an NLI (Natural Language Inference) classifier. Given a premise (a passage from a web page) and a hypothesis (a factual claim), determine the relationship.

Reply with exactly one word:
- ENTAILMENT if the premise supports or implies the hypothesis
- CONTRADICTION if the premise contradicts the hypothesis
- NEUTRAL if the premise neither supports nor contradicts the hypothesis

Do not explain. One word only."""


async def check_entailment(
    premise: str,
    hypothesis: str,
    model: str = "gpt-4o-mini",
) -> str:
    """Check if premise entails hypothesis. Returns 'ENTAILMENT', 'CONTRADICTION', or 'NEUTRAL'."""
    prompt = f"Premise: {premise}\n\nHypothesis: {hypothesis}"
    response = await complete(
        prompt=prompt,
        model=model,
        system=_NLI_SYSTEM,
        temperature=0.0,
        max_tokens=5,
    )
    result = response.strip().upper()
    if result.startswith("ENTAIL"):
        return "ENTAILMENT"
    if result.startswith("CONTRA"):
        return "CONTRADICTION"
    return "NEUTRAL"
