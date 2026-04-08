"""Layer 6 — Deterministic extraction (the second slop killer).

Pure synchronous function. Wraps crawl4ai's JsonCssExtractionStrategy
against one page's HTML and returns raw dicts. No Pydantic validation here
(that happens in citer.py after provenance is attached). Zero LLM calls.

Schema validation is the structural anti-hallucination layer: either a
field matches the selector or it does not. There is no middle ground.
"""

from __future__ import annotations

from typing import Any

from smart_crawler.types import RawPage


def extract(page: RawPage, css_schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Run the CSS schema across the page. Return raw dicts, no Pydantic."""
    raise NotImplementedError("extractor.extract — Phase 2 stub")
