"""B3: smart-crawler reference implementation.

Pipeline: Tavily search → fetch_and_filter → generate_and_ground → grounded facts.
This is the system the benchmark exists to test. If it can't beat B5b (Tavily
answer) on noise_ratio without losing accuracy, the project's thesis is wrong.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from tavily import AsyncTavilyClient

from benchmark.harness.types import (
    BaselineId,
    BenchmarkQuery,
    RetrievedChunk,
    RetrievedContext,
)
from smart_crawler.citer import generate_and_ground
from smart_crawler.crawler import fetch_and_filter

load_dotenv()


class SmartCrawlerBaseline:
    id: BaselineId = "b3_smart"
    name: str = "smart-crawler (summary mode — fetch+filter → generate+ground)"

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY not set.")
        self._client = AsyncTavilyClient(api_key=api_key)
        self._model = model

    async def retrieve(
        self,
        query: BenchmarkQuery,
        shared_urls: list[str] | None = None,
    ) -> RetrievedContext:
        """Full smart-crawler summary pipeline.

        1. Search for URLs (Tavily) — same as other baselines for fairness
        2. Fetch + sanitize + filter + truncate (crawler.fetch_and_filter)
        3. Generate grounded answer (citer.generate_and_ground)
        4. Return grounded facts as RetrievedChunks
        """
        # Step 1: Get URLs
        if shared_urls:
            urls = shared_urls
        else:
            response = await self._client.search(
                query=query.question,
                max_results=5,
                include_raw_content=False,
                include_answer=False,
            )
            urls = [r["url"] for r in response.get("results", [])]

        if not urls:
            return RetrievedContext(
                chunks=[],
                fetched_at=datetime.now(timezone.utc),
                bytes_fetched=0,
            )

        # Step 2: Fetch + filter (sync → run in thread to avoid blocking event loop)
        pages = await asyncio.to_thread(fetch_and_filter, urls, query.question)
        total_bytes = sum(len(p.html.encode("utf-8")) for p in pages)

        if not pages:
            return RetrievedContext(
                chunks=[],
                fetched_at=datetime.now(timezone.utc),
                bytes_fetched=total_bytes,
            )

        # Step 3: Generate + ground (1 LLM call)
        facts = await generate_and_ground(
            query=query.question,
            pages=pages,
            model=self._model,
        )

        # Step 4: Convert Facts to RetrievedChunks for the harness
        chunks: list[RetrievedChunk] = []
        for fact in facts:
            # Each fact's data is the grounded claim text
            text = fact.data if isinstance(fact.data, str) else str(fact.data)
            # Use the first source's URL and quote
            source = fact.sources[0]
            chunks.append(
                RetrievedChunk(
                    text=text,
                    source_url=source.url,
                    quote=source.quote,
                    metadata={
                        "extracted_by": fact.extracted_by,
                        "confidence": fact.confidence,
                    },
                )
            )

        return RetrievedContext(
            chunks=chunks,
            fetched_at=datetime.now(timezone.utc),
            bytes_fetched=total_bytes,
        )
