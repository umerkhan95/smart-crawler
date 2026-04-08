"""Layer 7 — Grounding (the keystone).

This is the architectural keystone of smart-crawler. crawl4ai has ZERO
built-in grounding — its LLMExtractionStrategy returns no quote spans, no
offsets. Without this module we are just another scraper. With it, we are a
retrieval *trust* layer.

For deterministic records: builds Source(url, retrieved_at, quote=matched
text) directly from the CSS selector hit.

For llm_fallback records: verifies each field's quote actually exists in
page.fit_markdown (exact match first, then rapidfuzz partial_ratio >= 92).
Drops the record on failure and returns None — pipeline.py counts the drop
as an error. NO SILENT FALLBACKS.
"""

from __future__ import annotations

from typing import Any

from smart_crawler.types import ExtractedBy, Fact, RawPage


def attach_citations(
    record: dict[str, Any],
    page: RawPage,
    extracted_by: ExtractedBy,
) -> Fact | None:
    """Return a grounded Fact, or None if the record cannot be cited."""
    raise NotImplementedError("citer.attach_citations — Phase 2 stub")
