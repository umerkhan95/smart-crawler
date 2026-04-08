"""Layer 5 — Planning (the only LLM-as-planner step).

Produces an ExtractionPlan in at most TWO LLM calls per (query, domain):

1. Pydantic model inference  (research file 05, approach 1)
2. crawl4ai JsonElementExtractionStrategy.generate_schema for the CSS schema
   (research file 05, approach 2)

After this layer runs, no other layer reads page content with an LLM
except repairer.py (which only fires on failures and is bounded). This is
the layer that makes "≤5 LLM calls per query" achievable.
"""

from __future__ import annotations

from smart_crawler.types import ExtractionPlan, Query, RawPage


async def make_plan(query: Query, sample_pages: list[RawPage]) -> ExtractionPlan:
    """One ExtractionPlan per domain. ≤2 LLM calls. No persistence."""
    raise NotImplementedError("planner.make_plan — Phase 2 stub")
