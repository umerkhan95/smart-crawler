"""B5: Tavily Research — a direct competitor.

Pipeline: tavily.search(query, include_raw_content=True) -> chunks with
source URLs. Tavily does its own relevance filtering and content
extraction server-side. This baseline answers: "does smart-crawler beat
a purpose-built search API that already optimizes for LLM consumption?"

This is the hardest baseline to beat. If smart-crawler can't outperform
Tavily on noise_ratio without losing accuracy, the project's value
proposition weakens — Tavily is a single API call with no crawl4ai,
no planner, no CSS extraction.

Controlled mode: searches with query, filters results to shared_urls.
E2E mode: uses Tavily search results directly.
"""

from __future__ import annotations

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

load_dotenv()


class TavilyBaseline:
    id: BaselineId = "b5_tavily"
    name: str = "Tavily (search API with built-in extraction)"

    def __init__(self) -> None:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY not set.")
        self._client = AsyncTavilyClient(api_key=api_key)

    async def retrieve(
        self,
        query: BenchmarkQuery,
        shared_urls: list[str] | None = None,
    ) -> RetrievedContext:
        """Search via Tavily and return extracted content as chunks.

        Tavily returns pre-extracted, relevance-ranked content. Each
        result becomes a RetrievedChunk. No local processing — this
        measures what a commercial search API gives you out of the box.
        """
        response = await self._client.search(
            query=query.question,
            max_results=10,
            include_raw_content=True,
            include_answer=False,
        )

        results = response.get("results", [])
        chunks: list[RetrievedChunk] = []
        total_bytes = 0

        for r in results:
            url = r.get("url", "")

            # Controlled mode: only use results matching shared URLs
            if shared_urls is not None and url not in shared_urls:
                continue

            # Prefer raw_content (full extraction), fall back to content (snippet)
            text = r.get("raw_content") or r.get("content", "")
            if not text:
                continue

            total_bytes += len(text.encode("utf-8"))
            chunks.append(
                RetrievedChunk(
                    text=text,
                    source_url=url,
                    metadata={
                        "title": r.get("title", ""),
                        "score": r.get("score", 0.0),
                    },
                )
            )

        return RetrievedContext(
            chunks=chunks,
            fetched_at=datetime.now(timezone.utc),
            bytes_fetched=total_bytes,
        )
