"""B1: crawl4ai with default config.

Pipeline: AsyncWebCrawler(default) -> markdown -> one chunk per page.
This is the "what does crawl4ai actually do for noise reduction out of
the box" baseline. Critical comparison: smart-crawler must beat B1 to
justify its existence as a layer on top of crawl4ai.

Controlled mode: crawls shared_urls only.
E2E mode: uses crawl4ai's built-in link discovery from a search seed.
"""

from __future__ import annotations

from datetime import datetime, timezone

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

from benchmark.harness.types import (
    BaselineId,
    BenchmarkQuery,
    RetrievedChunk,
    RetrievedContext,
)

# Honest User-Agent identifying the benchmark
USER_AGENT = "smart-crawler-benchmark/0.1 (b1_crawl4ai baseline; +https://github.com/umerkhan95/smart-crawler)"


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
        markdown output (fit_markdown). No custom filters, no extraction
        strategy, no grounding. Just crawl4ai out of the box.
        """
        urls = shared_urls or await self._discover_urls(query)
        chunks: list[RetrievedChunk] = []
        total_bytes = 0

        browser_config = BrowserConfig(
            headless=True,
            user_agent=USER_AGENT,
        )
        crawl_config = CrawlerRunConfig()

        async with AsyncWebCrawler(config=browser_config) as crawler:
            for url in urls:
                try:
                    result = await crawler.arun(url=url, config=crawl_config)
                    if result.success and result.markdown:
                        total_bytes += len(result.html.encode("utf-8")) if result.html else 0
                        # Use fit_markdown if available (cleaner), else raw markdown
                        text = getattr(result, "fit_markdown", None) or result.markdown
                        if text:
                            chunks.append(
                                RetrievedChunk(
                                    text=text,
                                    source_url=url,
                                )
                            )
                except Exception:
                    # B1 uses default error handling — skip failures.
                    continue

        return RetrievedContext(
            chunks=chunks,
            fetched_at=datetime.now(timezone.utc),
            bytes_fetched=total_bytes,
        )

    async def _discover_urls(self, query: BenchmarkQuery) -> list[str]:
        """E2E mode: discover URLs from the query via Tavily."""
        from benchmark.harness import search as search

        return await search.search_urls(query.question, max_results=5)
