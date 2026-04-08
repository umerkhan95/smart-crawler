# smart-crawler — rules

## Purpose
**Benchmark first, library second.** This repository ships an open
benchmark for measuring web-retrieval token noise in LLM agents
(`benchmark/`) and a stateless reference implementation that wins it
(`smart_crawler/`). The benchmark is the primary asset; the library
exists to be one entry on the leaderboard, not a general-purpose scraping
framework. See [`benchmark/methodology.md`](benchmark/methodology.md).

Every retrieval call is self-contained: no implicit cache, no database,
no on-disk artifacts. An optional `cache: CacheProtocol` parameter lets
callers BYO storage; smart-crawler ships no implementation.

## Design rules (non-negotiable)
- **Benchmark is the product.** Every implementation choice in
  `smart_crawler/` must be justifiable by its effect on the benchmark's
  two axes: noise ratio (lower) and answer accuracy (no regression). If a
  feature does not move either axis, it does not ship.
- **Stateless by default; optional cache is a borrowed protocol.** No
  implicit cache, no database, no on-disk artifacts. The library accepts
  an optional `cache: CacheProtocol | None = None` parameter so callers
  can pass `dict`/`diskcache`/`redis`/etc. smart-crawler ships zero cache
  implementations and no default. The library has no state; it borrows one
  when given one.
- **HTML sanitization + spotlighting before any LLM sees content.** The
  planner is the highest-value prompt-injection target (a poisoned plan
  contaminates every page on a domain). Strip `<script>`, `<iframe>`,
  `<meta>`, and event handlers. Apply Microsoft Spotlighting datamarking.
  Schema-sanity-check the planner's output before trusting it. This is a
  hard rule, not a best-effort.
- **Strict SRP**: every module does one thing. Planner plans, probe probes,
  crawler crawls, extractor extracts, repairer repairs. No god modules.
- **Plain functions by default**. Classes only when state or polymorphism
  genuinely requires them.
- **Modules do not import each other laterally**. Composition happens in
  `smart_crawler/pipeline.py` (or the public API), not inside leaf modules.
- **Schemas at every boundary**. Pydantic in, Pydantic out. No dict soup.
- **Every returned fact carries provenance**: url, retrieved_at, quote.
  Facts without provenance are not returned. `citer.py` is the architectural
  keystone, not a thin module — crawl4ai's `LLMExtractionStrategy` has zero
  built-in grounding, so we own provenance end-to-end.
- **LLM is a planner, not a reader**. Default `Budget.max_llm_calls = 5`,
  but this is a default the caller can dial up — not a hard wall. Bulk
  extraction is deterministic (CSS/XPath).
- **Fail loud at boundaries**. Don't swallow crawl/extraction errors into
  empty results — surface them with a reason.
- **No silent fallbacks**. If structured extraction fails and we fall back
  to LLM extraction, the result must be tagged `extracted_by="llm_fallback"`.

## Politeness defaults (OSS hygiene)
- Respect `robots.txt` by default (opt-out, not opt-in)
- Conservative concurrency via `MemoryAdaptiveDispatcher`
- Real `User-Agent` identifying smart-crawler + version
- Document clearly: re-running the same query re-fetches everything

## Two modes
- `structured` — Pydantic schema, deterministic, hallucination-proof
- `summary`    — compressed prose with mandatory quote+url grounding

## What NOT to build
- No generic "AI scraper" marketing fluff
- No backwards-compat shims (pre-1.0)
- No speculative abstractions for sites we haven't hit yet
- No CLI until the library API is stable

## Testing
- Unit tests per module (no network)
- Integration tests hit real sites behind a cassette/replay layer
- Never mock crawl4ai in integration tests — use recorded fixtures

## Git / commits
- No watermarks, no "Generated with Claude" footers, no emoji in commits
- Never add `Co-Authored-By` lines
- Commit messages describe the change and the why, nothing else

## Stack
- Python 3.12+
- crawl4ai (latest)
- pydantic v2
- uv for env + deps
- ruff + pytest
