"""Layer 3 — Fetching. The only module in smart-crawler that touches the network.

fetch_and_filter(): summary-mode pipeline (requests + BeautifulSoup).
  Domain blocklisting, sanitization, JS-wall detection, BM25 relevance gate,
  query-aware smart truncation. Synchronous; wrap in asyncio.to_thread.
crawl(): structured-mode pipeline (crawl4ai). Phase 3 stub.

Zero LLM calls. Both functions return Pydantic types at the boundary.
"""

from __future__ import annotations

import logging
import re
import string
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from smart_crawler.types import Budget, CrawlBatch, ExtractionPlan, RawPage

logger = logging.getLogger(__name__)

# -- Tunable constants -------------------------------------------------------

MAX_CONTENT_LENGTH: int = 16_000
MIN_RELEVANCE: float = 0.3
_REQUEST_TIMEOUT: int = 15
_USER_AGENT: str = "smart-crawler/0.1 (+https://github.com/umerkhan95/smart-crawler)"

_SANITIZE_TAGS: frozenset[str] = frozenset(
    {"script", "style", "iframe", "object", "embed", "meta", "link", "noscript", "form"}
)
_BOILERPLATE_TAGS: frozenset[str] = frozenset({"nav", "footer", "header", "aside"})
_EVENT_HANDLER_RE: re.Pattern[str] = re.compile(r"^on\w+$", re.IGNORECASE)

# Domains known to require JS rendering or login — skip before fetching.
_BLOCKED_DOMAINS: frozenset[str] = frozenset({
    "linkedin.com", "instagram.com", "facebook.com",
    "reddit.com", "quora.com", "twitter.com", "x.com",
    "tiktok.com", "pinterest.com",
})

_STOP_WORDS: frozenset[str] = frozenset(
    {"the", "a", "an", "is", "are", "was", "were", "of", "in", "to", "and",
     "or", "for", "on", "at", "by", "with", "from", "what", "who", "how",
     "when", "where", "which", "that", "this", "it", "do", "does", "did",
     "has", "have", "had", "be", "been", "being", "not", "no", "as", "but"}
)

# -- Internal helpers ---------------------------------------------------------

def _is_blocked(url: str) -> str | None:
    """Return a skip reason if the URL's domain is blocked, else None.

    urlparse prevents "notreddit.com" from matching "reddit.com". Strips "www.".
    """
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return "unparseable URL"
    host = host.removeprefix("www.")
    for blocked in _BLOCKED_DOMAINS:
        if host == blocked or host.endswith("." + blocked):
            return f"domain {blocked!r} requires JS rendering or login"
    return None


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


def _relevance(text: str, query: str) -> float:
    r"""Fraction of non-stop query words matched as whole words (\b boundary).

    "art" does not match "article". Returns 0.0 if no content words.
    """
    query_words = set(_tokenize(query)) - _STOP_WORDS
    if not query_words:
        return 0.0
    text_lower = text.lower()
    matched = sum(
        1 for w in query_words
        if re.search(rf"\b{re.escape(w)}\b", text_lower)
    )
    return matched / len(query_words)


def _smart_truncate(full_text: str, query: str, max_length: int) -> str:
    """Keep the first paragraph plus the highest-scoring ones up to max_length.

    Scores by query-word hit count; reassembles in original document order.
    """
    if len(full_text) <= max_length:
        return full_text

    paragraphs = [p.strip() for p in re.split(r"\n\n+", full_text) if p.strip()]
    if not paragraphs:
        return full_text[:max_length]
    if len(paragraphs) == 1:
        paragraphs = [p.strip() for p in full_text.split("\n") if p.strip()]

    query_words = set(_tokenize(query)) - _STOP_WORDS

    def _score(para: str) -> int:
        para_lower = para.lower()
        return sum(
            1 for w in query_words
            if re.search(rf"\b{re.escape(w)}\b", para_lower)
        )

    first, rest = paragraphs[0], paragraphs[1:]
    scored_rest = sorted(enumerate(rest), key=lambda iv: _score(iv[1]), reverse=True)

    selected: set[int] = set()
    budget = max_length - len(first) - 2  # reserve 2 chars for the joiner

    for original_idx, para in scored_rest:
        cost = len(para) + 2
        if budget >= cost:
            selected.add(original_idx)
            budget -= cost
        elif budget > 20:
            selected.add(original_idx)
            break

    kept = [first] + [p for i, p in enumerate(rest) if i in selected]
    return "\n\n".join(kept)[:max_length]


# -- Public: summary-mode entry point ----------------------------------------


def fetch_and_filter(
    urls: list[str],
    query: str,
    budget: Budget | None = None,
) -> list[RawPage]:
    """Fetch, sanitize, filter, and truncate pages for the summary pipeline.

    Steps: (1) domain blocklist before fetch, (2) HTTP GET, (3) sanitize HTML,
    (4) JS-wall detection, (5) word-boundary BM25 relevance gate,
    (6) smart paragraph-ranked truncation.

    Blocked URLs emit a RawPage with empty fit_markdown and url_skipped_reason
    in metadata. Other failures are logged and skipped. Never raises.
    """
    session = requests.Session()
    session.headers["User-Agent"] = _USER_AGENT
    pages: list[RawPage] = []

    for url in urls:
        fetched_at = datetime.now(UTC)

        # 1. Domain blocklist — save the HTTP round-trip.
        blocked_reason = _is_blocked(url)
        if blocked_reason:
            logger.warning("skipping blocked URL %s — %s", url, blocked_reason)
            pages.append(RawPage(
                url=url, html="", fit_markdown="", fetched_at=fetched_at,
                metadata={"url_skipped_reason": blocked_reason},
            ))
            continue

        # 2. HTTP fetch.
        try:
            response = session.get(url, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            raw_html = response.text
        except requests.RequestException as exc:
            logger.warning("fetch failed: %s — %s", url, exc)
            continue

        # 3. Sanitize + extract text.
        soup = _sanitize(raw_html)
        full_text = _to_markdown(soup)
        original_length = len(full_text)

        # 4. JS-wall detection: large HTML but no extractable text.
        if len(raw_html) > 5_000 and original_length < 200:
            logger.warning(
                "JS-walled page: %d bytes HTML → %d chars text"
                " — needs headless rendering: %s",
                len(raw_html), original_length, url,
            )
            continue
        if original_length < 200:
            logger.warning("page too short (%d chars) after sanitization: %s", original_length, url)
            continue

        # 5. Relevance gate (word-boundary BM25).
        score = _relevance(full_text, query)
        if score < MIN_RELEVANCE:
            logger.debug("relevance %.2f < %.2f, skipping %s", score, MIN_RELEVANCE, url)
            continue

        # 6. Smart truncation — keep relevant paragraphs, not just the head.
        truncated = original_length > MAX_CONTENT_LENGTH
        if truncated:
            fit_markdown = _smart_truncate(full_text, query, MAX_CONTENT_LENGTH)
            logger.warning("truncated %s from %d to %d chars", url, original_length, len(fit_markdown))
        else:
            fit_markdown = full_text

        pages.append(RawPage(
            url=url,
            html=raw_html,
            fit_markdown=fit_markdown,
            fetched_at=fetched_at,
            metadata={
                "relevance": round(score, 4),
                "original_length": original_length,
                "truncated": truncated,
            },
        ))

    return pages


# -- Public: structured-mode entry point (Phase 3 stub) ----------------------


async def crawl(
    plan: ExtractionPlan,
    budget: Budget,
    mode: Literal["best_first", "adaptive"],
    candidate_urls: list[str],
) -> CrawlBatch:
    """Phase 3 stub — wraps crawl4ai AsyncWebCrawler + MemoryAdaptiveDispatcher."""
    raise NotImplementedError("crawler.crawl — Phase 3 stub")
