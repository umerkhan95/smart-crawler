"""Layer 2 — URL discovery.

Produces a candidate URL queue from one of three sources, in order of
preference:

1. Caller-supplied seed_urls (fastest, most precise)
2. Search-engine seeded (when caller gave none)
3. Link expansion via BestFirst from a seed (last resort)

Discovery and fetching are different skills. This module decides what to
look at; crawler.py decides how to look at it. Mixing them is what makes
scrapers brittle. Zero LLM calls.
"""

from __future__ import annotations

from smart_crawler.types import Query, RouteDecision


async def discover(query: Query, decision: RouteDecision) -> list[str]:
    """Return an ordered candidate URL list with no duplicates."""
    raise NotImplementedError("discoverer.discover — Phase 2 stub")
