# smart-crawler — rules

## Purpose
A stateless, open-source retrieval pipeline built on crawl4ai. A reasoning
LLM calls `smart_search()` and gets back schema-valid, cited facts. Every
call is self-contained: no database, no cache, no on-disk artifacts.

## Design rules (non-negotiable)
- **Stateless**. No persistence layer, no cache, no on-disk artifacts. Every
  `smart_search()` call is self-contained. Users who want caching wrap us;
  we do not wrap them.
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
