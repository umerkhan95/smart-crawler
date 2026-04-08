"""Layer 1 — Routing.

Decides how much effort a query deserves. Pure function, no I/O, no LLM.
The only place that picks between snippet / single_page / deep_crawl /
adaptive_crawl. Without this layer every query burns the maximum budget.

Heuristic rules (research file 03, lesson "effort scales with difficulty"):
- caller-supplied seed_urls           → single_page or deep_crawl
- schema present + ≤5 entities        → single_page per entity
- schema present + bulk job           → deep_crawl
- no schema, broad question           → adaptive_crawl
- "what is X" / "define X" one-shot   → snippet
"""

from __future__ import annotations

from smart_crawler.types import Query, RouteDecision


def route(query: Query) -> RouteDecision:
    """Pick a branch + a per-branch budget. Pure, no side effects."""
    raise NotImplementedError("router.route — Phase 2 stub")
