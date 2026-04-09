"""Layers 0 + 9 — Composition.

This is the ONLY module that imports from sibling worker modules. Every
worker (router, discoverer, crawler, planner, probe, extractor, repairer,
citer) is imported here and nowhere else. Workers do not import each other.

Two execution paths:
- run_summary():     query → search → fetch+filter → generate+ground → Result
                     (implemented — the path the benchmark tests)
- run():             full structured pipeline (Phase 3 — raises NotImplementedError)
"""

from __future__ import annotations

import asyncio
import logging

from smart_crawler import citer as citer
from smart_crawler import crawler as crawler
from smart_crawler.types import (
    Fact,
    Query,
    Result,
    RetrievalError,
)

logger = logging.getLogger(__name__)


async def run_summary(
    query: Query,
    urls: list[str],
    model: str = "gpt-4o-mini",
) -> Result:
    """Summary-mode pipeline: the path that competes with B5b.

    1. Fetch + filter pages (crawler.fetch_and_filter — sync, run in thread)
    2. Generate grounded answer (citer.generate_and_ground — async, 1 LLM call)
    3. Package as Result

    If citer returns no grounded facts, the Result has zero facts and an
    error entry. The caller decides how to handle it (the benchmark scores
    it as accuracy=0).
    """
    errors: list[RetrievalError] = []

    # L3+L4: fetch + sanitize + filter + truncate (sync → run in thread)
    pages = await asyncio.to_thread(
        crawler.fetch_and_filter, urls, query.query
    )

    if not pages:
        errors.append(
            RetrievalError(
                layer="fetch",
                reason="All URLs failed to fetch or were filtered out by relevance.",
            )
        )
        return Result(
            query=query,
            facts=[],
            pages_crawled=0,
            llm_calls=0,
            stopped_because="error",
            errors=errors,
        )

    # L7: generate + ground (1 LLM call)
    facts: list[Fact] = await citer.generate_and_ground(
        query=query.query,
        pages=pages,
        model=model,
    )

    if not facts:
        errors.append(
            RetrievalError(
                layer="ground",
                reason="LLM generated an answer but no claims survived quote verification.",
            )
        )

    return Result(
        query=query,
        facts=facts,
        pages_crawled=len(pages),
        llm_calls=1,
        stopped_because="schema_satisfied" if facts else "error",
        errors=errors,
    )


async def run(query: Query) -> Result:
    """Full structured pipeline — Phase 3 stub.

    For the benchmark pilot, use run_summary() directly. This function
    will compose all 9 layers when the structured-mode workers are
    implemented.
    """
    raise NotImplementedError(
        "pipeline.run (structured mode) — Phase 3 stub. "
        "Use pipeline.run_summary() for the benchmark."
    )
