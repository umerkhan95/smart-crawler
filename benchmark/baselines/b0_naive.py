"""B0: the dumb floor.

Pipeline: requests.get(url) -> BeautifulSoup.get_text() -> one big chunk.
No filtering, no extraction, no grounding. This is the baseline that
exists to make every other baseline look good.

The point of B0 is reproducibility: anyone can replicate it in 20 lines.
If smart-crawler can't beat B0 on the benchmark, the project is wrong.

Controlled mode: fetches shared_urls only.
E2E mode: uses a search API to find URLs from the query, then fetches.
"""

from __future__ import annotations

from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from benchmark.harness.types import (
    BaselineId,
    BenchmarkQuery,
    RetrievedChunk,
    RetrievedContext,
)

# Honest User-Agent identifying the benchmark
USER_AGENT = "smart-crawler-benchmark/0.1 (b0_naive baseline; +https://github.com/umerkhan95/smart-crawler)"
REQUEST_TIMEOUT = 15


class NaiveBaseline:
    id: BaselineId = "b0_naive"
    name: str = "naive (requests + BeautifulSoup get_text)"

    async def retrieve(
        self,
        query: BenchmarkQuery,
        shared_urls: list[str] | None = None,
    ) -> RetrievedContext:
        """Fetch URLs, strip HTML with BS4, return as one chunk per page.

        Each page becomes a single RetrievedChunk with the full get_text()
        output. No filtering, no extraction. Maximum noise.
        """
        urls = shared_urls or await self._discover_urls(query)
        chunks: list[RetrievedChunk] = []
        total_bytes = 0

        for url in urls:
            try:
                resp = requests.get(
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                total_bytes += len(resp.content)

                soup = BeautifulSoup(resp.text, "html.parser")

                # Remove script and style elements (even B0 does this —
                # it's what get_text() users actually do in practice)
                for tag in soup(["script", "style"]):
                    tag.decompose()

                text = soup.get_text(separator="\n", strip=True)

                if text:
                    chunks.append(
                        RetrievedChunk(
                            text=text,
                            source_url=url,
                        )
                    )
            except (requests.RequestException, Exception):
                # B0 is the dumb floor — skip failures silently.
                # Other baselines should handle errors better.
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
