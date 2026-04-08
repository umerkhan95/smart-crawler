"""B1: crawl4ai with default config.

Pipeline: AsyncWebCrawler(default) -> markdown -> pass full markdown to
the answer LLM. This is the "what does crawl4ai actually do for noise
reduction out of the box" baseline. Critical comparison: smart-crawler
must beat B1 to justify its existence as a layer on top of crawl4ai.
"""

from __future__ import annotations

from benchmark.harness.types import BaselineId, BenchmarkQuery, RetrievedContext


class Crawl4aiBaseline:
    id: BaselineId = "b1_crawl4ai"
    name: str = "crawl4ai (default AsyncWebCrawler markdown)"

    async def retrieve(self, query: BenchmarkQuery) -> RetrievedContext:
        raise NotImplementedError("b1_crawl4ai.retrieve — Phase 2 stub")
