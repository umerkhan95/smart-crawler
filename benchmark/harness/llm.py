"""LLM API client — the single point of contact for all LLM calls in the harness.

Every LLM call in the benchmark (answer LLM + judge) flows through this
module. No other module is allowed to import openai directly. This
isolation means we can swap providers without touching metrics, runner,
or any baseline.

Reads OPENAI_API_KEY from environment / .env file.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

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
    max_tokens: int = 256,
) -> str:
    """Single completion call. Returns the assistant's text content.

    Used by both the answer LLM and the judge. Model is always passed
    explicitly — no hidden defaults.
    """
    client = _get_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""
