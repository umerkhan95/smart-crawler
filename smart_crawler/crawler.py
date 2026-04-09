"""Layer 3 — Fetching.

The only module in smart-crawler that touches the network.

Two entry points:

- fetch_and_filter(): summary-mode pipeline. Uses requests + BeautifulSoup.
  Synchronous. Wrap in asyncio.to_thread in the pipeline if needed.
  Handles HTML sanitization, event-handler stripping, boilerplate removal,
  crude BM25-style relevance filtering, and truncation.

- crawl(): structured-mode pipeline. Wraps crawl4ai AsyncWebCrawler.
  Phase 2 stub — raises NotImplementedError.

Zero LLM calls. Both functions return Pydantic types at the boundary.
"""

from __future__ import annotations

import logging
import re
import string
from datetime import UTC, datetime
from typing import Literal

import requests
from bs4 import BeautifulSoup

from smart_crawler.types import Budget, CrawlBatch, ExtractionPlan, RawPage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tunable constants — change these, not the logic.
# ---------------------------------------------------------------------------

MAX_CONTENT_LENGTH: int = 16_000
MIN_RELEVANCE: float = 0.3
_REQUEST_TIMEOUT: int = 15
_USER_AGENT: str = "smart-crawler/0.1 (+https://github.com/umerkhan95/smart-crawler)"

# Tags that carry executable content or embed external resources.
_SANITIZE_TAGS: frozenset[str] = frozenset(
    {"script", "style", "iframe", "object", "embed", "meta", "link", "noscript", "form"}
)

# Structural boilerplate that rarely contains answer-relevant content.
_BOILERPLATE_TAGS: frozenset[str] = frozenset({"nav", "footer", "header", "aside"})

# All on* event-handler attribute names — prompt-injection vector.
_EVENT_HANDLER_RE: re.Pattern[str] = re.compile(r"^on\w+$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sanitize(html: str) -> BeautifulSoup:
    """Parse HTML and strip executable / boilerplate content in-place."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(_SANITIZE_TAGS | _BOILERPLATE_TAGS):
        tag.decompose()

    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if _EVENT_HANDLER_RE.match(attr):
                del tag.attrs[attr]

    return soup


def _to_markdown(soup: BeautifulSoup) -> str:
    """Extract plain text from sanitized soup with paragraph breaks."""
    return soup.get_text(separator="\n", strip=True)


def _tokenize(text: str) -> list[str]:
    """Lowercase words with punctuation stripped — for relevance scoring."""
    translator = str.maketrans("", "", string.punctuation)
    return text.lower().translate(translator).split()


_STOP_WORDS: frozenset[str] = frozenset(
    {"the", "a", "an", "is", "are", "was", "were", "of", "in", "to", "and",
     "or", "for", "on", "at", "by", "with", "from", "what", "who", "how",
     "when", "where", "which", "that", "this", "it", "do", "does", "did",
     "has", "have", "had", "be", "been", "being", "not", "no", "as", "but"}
)


def _relevance(text: str, query: str) -> float:
    """Fraction of unique non-stop query words that appear anywhere in text.

    Crude BM25 approximation: good enough for the pilot. crawl4ai's
    BM25ContentFilter can replace this later without changing the interface.
    Returns 0.0 if the query has no content words.
    """
    query_words = set(_tokenize(query)) - _STOP_WORDS
    if not query_words:
        return 0.0
    text_lower = text.lower()
    matched = sum(1 for w in query_words if w in text_lower)
    return matched / len(query_words)


# ---------------------------------------------------------------------------
# Public: summary-mode entry point
# ---------------------------------------------------------------------------


def fetch_and_filter(
    urls: list[str],
    query: str,
    budget: Budget | None = None,
) -> list[RawPage]:
    """Fetch, sanitize, filter, and truncate pages for the summary pipeline.

    Steps per URL:
    1. HTTP GET with honest User-Agent and 15-second timeout.
    2. HTML sanitization: remove scripts, styles, iframes, event handlers,
       and structural boilerplate (nav/footer/header/aside).
    3. Plain-text extraction with paragraph-preserving separators.
    4. BM25-style relevance gate: skip pages scoring below MIN_RELEVANCE.
    5. Truncate to MAX_CONTENT_LENGTH characters.

    Failures are logged and skipped — this function never raises on a bad URL.
    The budget parameter is accepted for API compatibility but not yet used
    (URL-count limiting lives in the pipeline layer).

    Args:
        urls:   Ordered list of URLs to fetch.
        query:  The user's search query — used for relevance scoring.
        budget: Optional crawl budget (unused in this implementation).

    Returns:
        List of RawPage objects that passed the relevance filter, in fetch order.
    """
    session = requests.Session()
    session.headers["User-Agent"] = _USER_AGENT

    pages: list[RawPage] = []

    for url in urls:
        fetched_at = datetime.now(UTC)

        try:
            response = session.get(url, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            raw_html = response.text
        except requests.RequestException as exc:
            logger.warning("fetch failed: %s — %s", url, exc)
            continue

        soup = _sanitize(raw_html)
        full_text = _to_markdown(soup)
        original_length = len(full_text)

        if original_length < 200:
            logger.warning("page too short (%d chars) after sanitization: %s", original_length, url)
            continue

        score = _relevance(full_text, query)
        if score < MIN_RELEVANCE:
            logger.debug(
                "relevance %.2f < %.2f, skipping %s", score, MIN_RELEVANCE, url
            )
            continue

        truncated = original_length > MAX_CONTENT_LENGTH
        fit_markdown = full_text[:MAX_CONTENT_LENGTH] if truncated else full_text

        pages.append(
            RawPage(
                url=url,
                html=raw_html,
                fit_markdown=fit_markdown,
                fetched_at=fetched_at,
                metadata={
                    "relevance": round(score, 4),
                    "original_length": original_length,
                    "truncated": truncated,
                },
            )
        )

    return pages


# ---------------------------------------------------------------------------
# Public: structured-mode entry point (Phase 2 stub)
# ---------------------------------------------------------------------------


async def crawl(
    plan: ExtractionPlan,
    budget: Budget,
    mode: Literal["best_first", "adaptive"],
    candidate_urls: list[str],
) -> CrawlBatch:
    """Fetch + filter pages until budget or stop signal. Polite by default.

    Phase 2 stub. Will wrap crawl4ai AsyncWebCrawler with
    MemoryAdaptiveDispatcher. Two branches:
    - best_first: BestFirstCrawlingStrategy + KeywordRelevanceScorer
    - adaptive:   AdaptiveCrawler (summary mode only)
    """
    raise NotImplementedError("crawler.crawl — Phase 2 stub")
