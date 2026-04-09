"""B5: Tavily baselines — testing every relevant mode per the docs.

Tavily docs (https://docs.tavily.com/documentation/best-practices/)
specify a recommended agent workflow:
  Search → Filter by relevance → Extract with query + chunks_per_source

We benchmark four Tavily modes to be honest about what the API can do:

B5a: search(include_raw_content=True) — full pages, worst case
B5b: search(include_answer="advanced") — Tavily's generated answer
B5c: search() → extract(urls, query, chunks_per_source=3) — the
     recommended two-step workflow (the real competitor)
B5d: search(search_depth="advanced", chunks_per_source=3) — advanced
     search with server-side chunking in one call
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


def _get_client() -> AsyncTavilyClient:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY not set.")
    return AsyncTavilyClient(api_key=api_key)


# ---------------------------------------------------------------------------
# B5a: Full pages (worst case — anti-pattern per docs)
# ---------------------------------------------------------------------------


class TavilyRawBaseline:
    id: BaselineId = "b5_tavily"
    name: str = "Tavily search (raw content — worst case)"

    async def retrieve(
        self,
        query: BenchmarkQuery,
        shared_urls: list[str] | None = None,
    ) -> RetrievedContext:
        """search(include_raw_content=True) — dumps full pages."""
        client = _get_client()
        response = await client.search(
            query=query.question,
            max_results=5,
            search_depth="basic",
            include_raw_content=True,
            include_answer=False,
        )

        chunks, total_bytes = _results_to_chunks(response, shared_urls)
        return RetrievedContext(
            chunks=chunks,
            fetched_at=datetime.now(timezone.utc),
            bytes_fetched=total_bytes,
        )


# ---------------------------------------------------------------------------
# B5b: Tavily's generated answer (most compressed)
# ---------------------------------------------------------------------------


class TavilyAnswerBaseline:
    id: BaselineId = "b5_tavily"
    name: str = "Tavily search (include_answer=advanced)"

    async def retrieve(
        self,
        query: BenchmarkQuery,
        shared_urls: list[str] | None = None,
    ) -> RetrievedContext:
        """search(include_answer="advanced") — Tavily generates an answer."""
        client = _get_client()
        response = await client.search(
            query=query.question,
            max_results=5,
            search_depth="basic",
            include_answer="advanced",
            include_raw_content=False,
        )

        chunks: list[RetrievedChunk] = []
        total_bytes = 0

        # The generated answer is the primary content
        answer = response.get("answer", "")
        if answer:
            total_bytes += len(answer.encode("utf-8"))
            chunks.append(
                RetrievedChunk(
                    text=answer,
                    source_url="tavily:generated_answer",
                    metadata={"type": "generated_answer"},
                )
            )

        # Also include the snippets as supporting context
        snippet_chunks, snippet_bytes = _results_to_chunks(response, shared_urls)
        chunks.extend(snippet_chunks)
        total_bytes += snippet_bytes

        return RetrievedContext(
            chunks=chunks,
            fetched_at=datetime.now(timezone.utc),
            bytes_fetched=total_bytes,
        )


# ---------------------------------------------------------------------------
# B5c: Search → Extract (the recommended workflow per docs)
# ---------------------------------------------------------------------------


class TavilySearchExtractBaseline:
    id: BaselineId = "b5_tavily"
    name: str = "Tavily search → extract (recommended workflow)"

    async def retrieve(
        self,
        query: BenchmarkQuery,
        shared_urls: list[str] | None = None,
    ) -> RetrievedContext:
        """Two-step: search for URLs, then extract with query-focused chunks.

        This is the workflow Tavily's docs recommend for agents:
        Search → Filter by relevance → Extract with query + chunks_per_source
        """
        client = _get_client()

        # Step 1: Search for relevant URLs
        search_response = await client.search(
            query=query.question,
            max_results=5,
            search_depth="basic",
            include_raw_content=False,
            include_answer=False,
        )

        # Filter to shared_urls if in controlled mode
        urls = []
        for r in search_response.get("results", []):
            url = r.get("url", "")
            if shared_urls is not None and url not in shared_urls:
                continue
            if url:
                urls.append(url)

        if not urls:
            return RetrievedContext(
                chunks=[],
                fetched_at=datetime.now(timezone.utc),
                bytes_fetched=0,
            )

        # Step 2: Extract with query-focused chunking
        extract_response = await client.extract(
            urls=urls[:10],  # extract supports max 20
            query=query.question,
            chunks_per_source=3,
            extract_depth="basic",
            format="markdown",
        )

        chunks: list[RetrievedChunk] = []
        total_bytes = 0

        for r in extract_response.get("results", []):
            url = r.get("url", "")
            # When chunks_per_source + query is used, raw_content contains
            # the focused chunks, not the full page
            text = r.get("raw_content") or r.get("content", "")
            if text:
                total_bytes += len(text.encode("utf-8"))
                chunks.append(
                    RetrievedChunk(
                        text=text,
                        source_url=url,
                        metadata={"method": "search_then_extract"},
                    )
                )

        return RetrievedContext(
            chunks=chunks,
            fetched_at=datetime.now(timezone.utc),
            bytes_fetched=total_bytes,
        )


# ---------------------------------------------------------------------------
# B5d: Advanced search with chunks (one-call alternative)
# ---------------------------------------------------------------------------


class TavilyAdvancedChunksBaseline:
    id: BaselineId = "b5_tavily"
    name: str = "Tavily advanced search (chunks_per_source=3)"

    async def retrieve(
        self,
        query: BenchmarkQuery,
        shared_urls: list[str] | None = None,
    ) -> RetrievedContext:
        """search(search_depth="advanced", chunks_per_source=3).

        Single call with server-side chunking. Advanced depth provides
        higher relevance at the cost of latency.
        """
        client = _get_client()
        response = await client.search(
            query=query.question,
            max_results=5,
            search_depth="advanced",
            chunks_per_source=3,
            include_raw_content=False,
            include_answer=False,
        )

        chunks, total_bytes = _results_to_chunks(response, shared_urls)
        return RetrievedContext(
            chunks=chunks,
            fetched_at=datetime.now(timezone.utc),
            bytes_fetched=total_bytes,
        )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _results_to_chunks(
    response: dict,
    shared_urls: list[str] | None,
) -> tuple[list[RetrievedChunk], int]:
    """Convert Tavily search results to RetrievedChunks."""
    chunks: list[RetrievedChunk] = []
    total_bytes = 0

    for r in response.get("results", []):
        url = r.get("url", "")
        if shared_urls is not None and url not in shared_urls:
            continue

        # Use raw_content if present (full page), else content (snippet)
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

    return chunks, total_bytes
