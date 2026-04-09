"""Search API client — URL discovery for the benchmark harness.

Uses Tavily for web search. Single point of contact — no other module
imports tavily directly. This isolation means we can swap search
providers without touching runner, baselines, or metrics.

Reads TAVILY_API_KEY from environment / .env file.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from tavily import AsyncTavilyClient

load_dotenv()

_client: AsyncTavilyClient | None = None


def _get_client() -> AsyncTavilyClient:
    global _client
    if _client is None:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError(
                "TAVILY_API_KEY not set. Add it to .env or export it."
            )
        _client = AsyncTavilyClient(api_key=api_key)
    return _client


async def search_urls(
    query: str,
    max_results: int = 5,
) -> list[str]:
    """Search the web for URLs relevant to a query.

    Returns a list of URLs, ordered by relevance. Used by:
    - runner.discover_shared_urls() in controlled mode
    - baseline._discover_urls() in e2e mode (baselines can import this)
    """
    client = _get_client()
    response = await client.search(
        query=query,
        max_results=max_results,
        include_answer=False,
        include_raw_content=False,
    )
    return [r["url"] for r in response.get("results", [])]
