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

from benchmark.harness.types import BaselineId, BenchmarkQuery, RetrievedContext


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
        raise NotImplementedError("b0_naive.retrieve — Phase 2 stub")
