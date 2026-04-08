"""Layer 8 — LLM repair fallback (loud, bounded, tagged).

Called only when extractor.extract() returned empty for a page. Builds an
LLMExtractionStrategy(input_format="fit_markdown") with the
pydantic_model_spec schema and the explicit instruction to return
{value, quote} per field (research file 04).

Constraints:
- Bounded to 1 retry per page
- Failures are loud — they bubble up to pipeline.py and increment errors
- Every output is tagged extracted_by="llm_fallback" by citer.py
- This is the ONLY module besides planner.py allowed to make an LLM call
"""

from __future__ import annotations

from typing import Any

from smart_crawler.types import ExtractionPlan, RawPage


async def repair(
    page: RawPage,
    plan: ExtractionPlan,
) -> dict[str, Any] | None:
    """Last-ditch LLM extraction with mandatory {value, quote} per field."""
    raise NotImplementedError("repairer.repair — Phase 2 stub")
