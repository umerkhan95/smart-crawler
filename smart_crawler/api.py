"""Public API. The only function external callers should use.

Wraps pipeline.run_summary() for summary mode (the benchmark path) and
pipeline.run() for structured mode (Phase 3 stub).
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
    model: str = "gpt-4o-mini",
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

    if mode == "summary":
        if not q.seed_urls:
            # Discover URLs via search if none provided
            from benchmark.harness.search import search_urls

            urls = await search_urls(query, max_results=5)
        else:
            urls = q.seed_urls
        return await pipeline.run_summary(q, urls, model=model)

    return await pipeline.run(q)
