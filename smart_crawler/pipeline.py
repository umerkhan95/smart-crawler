"""Layers 0 + 9 — Composition.

This is the ONLY module that imports from sibling worker modules. Every
worker (router, discoverer, crawler, planner, probe, extractor, repairer,
citer) is imported here and nowhere else. Workers do not import each other.

Responsibilities:
- L0 Intake     — validate/normalize the Query
- L1 Route      — call router.route
- L2 Discover   — call discoverer.discover (or use seed_urls)
- L3 Fetch      — call crawler.crawl (streamed)
- L5 Plan       — call planner.make_plan (1-2 LLM calls)
- L5b Probe     — call probe.probe_plan, re-plan once on coverage failure
- L6 Extract    — call extractor.extract per page
- L7 Ground     — call citer.attach_citations per record
- L8 Repair     — call repairer.repair on extraction failures (bounded)
- L9 Stop       — schema-completeness OR budget OR adaptive plateau

Owns the structured-mode stop loop: schema-completeness, NOT crawl4ai's
saturation metric. Reserve AdaptiveCrawler's saturation for `summary` mode.
"""

from __future__ import annotations

from smart_crawler import citer as citer
from smart_crawler import crawler as crawler
from smart_crawler import discoverer as discoverer
from smart_crawler import extractor as extractor
from smart_crawler import planner as planner
from smart_crawler import probe as probe
from smart_crawler import repairer as repairer
from smart_crawler import router as router
from smart_crawler.types import Query, Result


async def run(query: Query) -> Result:
    """Compose the 9 layers into a single retrieval call. Stateless."""
    # L0 intake (validation / defaults already applied by api.smart_search)
    # L1 route
    _decision = router.route(query)
    # L2 discover
    _candidates = await discoverer.discover(query, _decision)
    # L5 plan (needs sample pages — fetch a couple via crawler first)
    # L5b probe → re-plan once on failure
    # L3 fetch the rest
    # L6 extract per page
    # L7 ground per record
    # L8 repair on failures (bounded, tagged)
    # L9 stop on schema-completeness | budget | plateau
    _ = (citer, crawler, extractor, planner, probe, repairer)  # silence unused-import until impl
    raise NotImplementedError("pipeline.run — Phase 2 stub")
