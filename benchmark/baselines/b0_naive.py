"""B0: the dumb floor.

Pipeline: requests.get(url) -> BeautifulSoup.get_text() -> pass full text
to the answer LLM. No filtering, no extraction, no grounding. This is the
baseline that exists to make every other baseline look good.

The point of B0 is reproducibility: anyone can replicate it in 20 lines.
If smart-crawler can't beat B0 on the benchmark, the project is wrong.
"""

from __future__ import annotations

from datetime import datetime

from benchmark.harness.types import BaselineId, BenchmarkQuery, RetrievedContext


class NaiveBaseline:
    id: BaselineId = "b0_naive"
    name: str = "naive (requests + BeautifulSoup get_text)"

    async def retrieve(self, query: BenchmarkQuery) -> RetrievedContext:
        raise NotImplementedError("b0_naive.retrieve — Phase 2 stub")
