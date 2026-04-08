"""Public API. The only function external callers should use.

Wraps pipeline.run() with type coercion (Pydantic class -> JSON schema dict,
default Budget, etc). This is the L0 intake boundary.
"""

from __future__ import annotations

from typing import Any

from smart_crawler import pipeline as pipeline
from smart_crawler.types import Budget, Mode, Query, Result


async def smart_search(
    query: str,
    mode: Mode = "structured",
    schema: dict[str, Any] | None = None,
    seed_urls: list[str] | None = None,
    freshness: str | None = None,
    budget: Budget | None = None,
    must_cite: bool = True,
) -> Result:
    """Offloaded web retrieval.

    Returns schema-valid, cited facts. The reasoning LLM never reads raw
    HTML — only what passes extraction + grounding. Stateless: every call
    is self-contained, no caching, no persistence.
    """
    q = Query(
        query=query,
        mode=mode,
        schema_hint=schema,
        seed_urls=seed_urls or [],
        freshness=freshness,
        budget=budget or Budget(),
        must_cite=must_cite,
    )
    return await pipeline.run(q)
