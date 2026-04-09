"""B3: smart-crawler reference implementation.

Pipeline: Tavily search → fetch_and_filter → generate_and_ground → grounded facts.
Now uses 3-tier verification (string match → NLI → fuzzy → low_confidence tag).
Never returns empty — low_confidence facts are tagged, not dropped.
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
    name: str = "smart-crawler (3-tier grounding: string → NLI → fuzzy)"

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
        """Full smart-crawler summary pipeline with 3-tier grounding."""
        # Step 1: Get URLs (8 results for better coverage)
        if shared_urls:
            urls = shared_urls
        else:
            response = await self._client.search(
                query=query.question,
                max_results=8,
                include_raw_content=False,
                include_answer=False,
            )
            urls = [r["url"] for r in response.get("results", [])]

        if not urls:
            return RetrievedContext(
                chunks=[], fetched_at=datetime.now(timezone.utc), bytes_fetched=0,
            )

        # Step 2: Fetch + filter (sync → thread)
        pages = await asyncio.to_thread(fetch_and_filter, urls, query.question)
        total_bytes = sum(len(p.html.encode("utf-8")) for p in pages if p.html)

        if not pages or all(not p.fit_markdown for p in pages):
            return RetrievedContext(
                chunks=[], fetched_at=datetime.now(timezone.utc), bytes_fetched=total_bytes,
            )

        # Filter out empty pages (blocked domains return empty fit_markdown)
        valid_pages = [p for p in pages if p.fit_markdown]

        if not valid_pages:
            return RetrievedContext(
                chunks=[], fetched_at=datetime.now(timezone.utc), bytes_fetched=total_bytes,
            )

        # Step 3: Generate + ground (1 LLM call + NLI verification)
        facts = await generate_and_ground(
            query=query.question,
            pages=valid_pages,
            model=self._model,
        )

        # Step 4: Convert Facts to RetrievedChunks
        # Use Fact.answer (the synthesized answer) as the primary text
        # Use Fact.sources[0].quote as the supporting evidence
        chunks: list[RetrievedChunk] = []
        for fact in facts:
            # Primary text: the answer sentence if available, else the claim/data
            text = fact.answer or (fact.data if isinstance(fact.data, str) else str(fact.data))
            source = fact.sources[0]
            chunks.append(
                RetrievedChunk(
                    text=text,
                    source_url=source.url,
                    quote=source.quote,
                    metadata={
                        "extracted_by": fact.extracted_by,
                        "confidence": fact.confidence,
                        "grounding_level": fact.grounding_level,
                    },
                )
            )

        return RetrievedContext(
            chunks=chunks,
            fetched_at=datetime.now(timezone.utc),
            bytes_fetched=total_bytes,
        )
