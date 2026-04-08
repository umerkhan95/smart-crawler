"""Layer 5b — Plan validation.

Runs an ExtractionPlan against one already-fetched page (no network) and
reports per-field hit rate. If coverage < 0.5, the caller should reject the
plan and re-plan once. Zero LLM calls.
"""

from __future__ import annotations

from smart_crawler.types import ExtractionPlan, ProbeReport, RawPage


async def probe_plan(plan: ExtractionPlan, page: RawPage) -> ProbeReport:
    """Cheap sanity check on a plan before running it across N pages."""
    raise NotImplementedError("probe.probe_plan — Phase 2 stub")
