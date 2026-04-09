"""B1: crawl4ai with default config.

Pipeline: AsyncWebCrawler(default) -> markdown -> one chunk per page.
This is the "what does crawl4ai actually do for noise reduction out of
the box" baseline. Critical comparison: smart-crawler must beat B1 to
justify its existence as a layer on top of crawl4ai.

Controlled mode: crawls shared_urls only.
E2E mode: uses crawl4ai's built-in link discovery from a search seed.
"""

from __future__ import annotations

from benchmark.harness.types import BaselineId, BenchmarkQuery, RetrievedContext


class Crawl4aiBaseline:
    id: BaselineId = "b1_crawl4ai"
    name: str = "crawl4ai (default AsyncWebCrawler markdown)"

    async def retrieve(
        self,
        query: BenchmarkQuery,
        shared_urls: list[str] | None = None,
    ) -> RetrievedContext:
        """Fetch with AsyncWebCrawler default config, return markdown chunks.

        Each page becomes a single RetrievedChunk with crawl4ai's default
        markdown output. No custom filters, no extraction strategy, no
        grounding. Just crawl4ai out of the box.
        """
        raise NotImplementedError("b1_crawl4ai.retrieve — Phase 2 stub")
