# smart-crawler

**An open benchmark for measuring web-retrieval token noise in LLM agents — and a stateless reference implementation that wins it.**

> Roughly half of all electricity, water, money, and latency that goes into LLM
> web retrieval today is consumed processing content that contributes nothing
> to the answer. That is an industry-scale inefficiency, and the fix is a
> software pattern, not a model upgrade. — [Epic #1](https://github.com/umerkhan95/smart-crawler/issues/1)

This repository ships **two things**:

1. **The benchmark** (`benchmark/`) — a reproducible methodology for measuring
   how much of an LLM agent's web-retrieval context is signal vs noise,
   *without sacrificing answer accuracy*. Built on FreshQA + BrowseComp query
   sets, with defined baselines (naive `requests`+BS4, crawl4ai default,
   Firecrawl, LangExtract). The benchmark is the primary asset.

2. **The library** (`smart_crawler/`) — a stateless Python reference
   implementation built on crawl4ai. The reasoning LLM calls
   `smart_search()` and gets back schema-valid, cited facts instead of raw
   HTML. The library exists to be one entry on the leaderboard, not to be a
   general-purpose scraping framework.

## Why a benchmark, not just a library

There is no standard way to measure "how much of my retrieval context is
slop." RAGAS Context Precision, RULER, HHEM all measure adjacent things.
crawl4ai, Firecrawl, LangExtract, llm-scraper all claim to be "cleaner" but
none publish a falsifiable methodology against shared baselines. Without a
shared yardstick, every team's "we reduced noise by X%" is a marketing
claim.

smart-crawler proposes one. If the methodology is adopted, the library
becomes a reference; if a better implementation comes along, it can submit
itself as a baseline and win.

## The two metrics that matter (both, simultaneously)

A retrieval system can trivially reduce noise to zero by returning nothing.
Quality must be measured alongside cost. The benchmark reports a
**two-axis score**:

| Axis | Metric | What it measures |
|---|---|---|
| **Cost** | `noise_ratio` | Tokens in the LLM's context not in the minimal answer span (lower = better) |
| **Quality** | `answer_accuracy` | Does the LLM still produce the correct answer given the retrieved context? (higher = better) |

A system "wins" only if it improves noise *without* losing accuracy. See
[`benchmark/methodology.md`](benchmark/methodology.md) for the full spec.

## The reference implementation

```python
from smart_crawler import smart_search

result = smart_search(
    query="find CEO and HQ of these 20 AI startups",
    mode="structured",          # or "summary"
    schema=CompanyInfo,         # optional Pydantic model; inferred if absent
    seed_urls=["https://example.com/about"],   # optional
    budget={"max_pages": 50, "max_llm_calls": 8},
    must_cite=True,
)

for fact in result.facts:
    print(fact.data, fact.sources)   # every field carries url + quote + ts
```

**Design rules** (see [`CLAUDE.md`](CLAUDE.md) for the full list):

- **Stateless by default.** No database, no implicit cache. Optional
  `cache: CacheProtocol` parameter for callers who want to BYO storage —
  smart-crawler ships no implementation.
- **Strict SRP.** Each module does one thing. Workers don't import workers.
- **Provenance is non-optional.** Every returned fact carries `url + verbatim
  quote + retrieved_at`. Ungrounded facts are dropped, never returned.
- **The LLM is a planner, not a reader.** Bulk extraction is deterministic.
- **No silent fallbacks.** LLM-extracted facts are tagged
  `extracted_by="llm_fallback"`.
- **Polite by default.** Respects `robots.txt`, conservative concurrency,
  honest User-Agent.
- **Injection-resistant.** HTML sanitization and Microsoft Spotlighting
  applied to all content the planner reads.

## Architecture

```
smart_search(query, mode, schema?, budget)
        │
        ▼
   ROUTE       snippet | single | deep | adaptive
   DISCOVER    crawl4ai BestFirst + relevance scorer
   FETCH       only network module; polite, sanitized
   PLAN        ≤2 LLM calls per domain (generate_schema)
   PROBE       coverage check + re-plan once
   EXTRACT     deterministic CSS/XPath, no LLM
   GROUND      attach {url, quote, retrieved_at}; drop ungrounded
   REPAIR      bounded LLM fallback, tagged
   STOP        required-fields-filled OR budget OR info-gain plateau
        │
        ▼
   Result(facts=[...], errors=[...])
```

Everything between route and stop lives in local variables. Stateless.

## Status

- ✅ Phase 0 — scaffolding
- ✅ Phase 1 — research dossier (`research/`)
- ✅ Phase 1b — design validation (`research/validation/`)
- ⏳ Phase 2 — benchmark methodology spec ([Issue #3](https://github.com/umerkhan95/smart-crawler/issues/3))
- ⏳ Phase 3 — reference implementation (Issue [#2](https://github.com/umerkhan95/smart-crawler/issues/2))

See [`plans.md`](plans.md) for the full build plan and [Issue #1](https://github.com/umerkhan95/smart-crawler/issues/1) for the problem statement.

## License

Apache-2.0
