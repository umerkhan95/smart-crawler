"""Layer 3 — Fetching.

The only module in smart-crawler that touches the network. Wraps crawl4ai's
AsyncWebCrawler. Handles JS rendering, redirects, retries, timeouts,
robots.txt, rate limiting, and politeness. Always uses
MemoryAdaptiveDispatcher.

Two crawl modes:
- best_first: BestFirstCrawlingStrategy + KeywordRelevanceScorer +
              URLPatternFilter — for known-shape extraction.
- adaptive:   AdaptiveCrawler with confidence_threshold — for open-ended
              `summary` mode only. Do NOT use for structured mode (research
              file 02: saturation metric quits early on sparse-fact queries).

Streams pages so pipeline.py can early-stop on schema-completeness. Returns
stopped_because so the caller knows whether to retry. Zero LLM calls.
"""

from __future__ import annotations

from typing import Literal

from smart_crawler.types import Budget, CrawlBatch, ExtractionPlan


async def crawl(
    plan: ExtractionPlan,
    budget: Budget,
    mode: Literal["best_first", "adaptive"],
    candidate_urls: list[str],
) -> CrawlBatch:
    """Fetch + filter pages until budget or stop signal. Polite by default."""
    raise NotImplementedError("crawler.crawl — Phase 2 stub")
