# smart-crawler

**A stateless, open-source retrieval pipeline for LLM agents. Built on crawl4ai.**

Your reasoning LLM decides *what* to know. smart-crawler decides *how* to get it
and returns clean, cited, schema-valid facts. No database. No cache. No infra.
One function call in, structured facts out.

## Why

LLM agents that browse the web today read raw pages and drown in slop —
nav bars, ads, sidebars, related-article rails, cookie banners. Context
windows fill with noise and reasoning anchors on the wrong things.

smart-crawler sits between the reasoning LLM and the web as a *retrieval
offload layer*. The LLM never reads raw pages. It calls `smart_search()`
and gets back only what passes schema validation and grounding checks.

## Contract

```python
from smart_crawler import smart_search

result = smart_search(
    query="find CEO and HQ of these 20 AI startups",
    mode="structured",          # or "summary"
    schema=CompanyInfo,         # optional Pydantic model; inferred if absent
    budget={"max_pages": 50, "max_llm_calls": 5},
    must_cite=True,
)

for fact in result.facts:
    print(fact.data, fact.sources)   # every field carries url + quote + ts
```

Returns records with `data`, `sources` (url + retrieved_at + quote), and
`confidence`. Unvalidated content never reaches the caller.

## Architecture (in-memory, one call)

```
smart_search(query, mode, schema?, budget)
        │
        ▼
   ROUTE       snippet?  single page?  deep?  adaptive?
        │
        ▼
   DISCOVER    crawl4ai BestFirst + relevance scorer
               PruningContentFilter + BM25 BEFORE the LLM sees anything
        │
        ▼
   PLAN        1 LLM call: sample pages → extraction schema
        │
        ▼
   EXTRACT     deterministic CSS/XPath, no LLM
        │
        ▼
   GROUND      attach {url, quote, retrieved_at} to every field
               drop facts without grounding
        │
        ▼
   STOP        schema complete? budget exhausted? info-gain plateaued?
        │
        ▼
   Result(facts=[...], errors=[...])
```

Everything between route and stop lives in local variables. Nothing touches
disk. Nothing persists between calls.

## Two modes

| Mode | Output | Use when |
|---|---|---|
| `structured` | Pydantic-typed records | You know the shape: prices, specs, profiles, listings |
| `summary` | Compressed prose with mandatory quote+url citations | Open-ended research questions |

## Design principles

- **Stateless**. No cache, no database, no learned artifacts. Stateless is a
  feature for an LLM tool — no staleness, no invalidation.
- **Slop is rejected at the extraction boundary**, not filtered in reasoning
  context. Schema validation can't hallucinate.
- **Every fact is grounded**. Provenance is non-optional.
- **The LLM is a planner, not a reader.** Default <5 LLM calls per query;
  bulk extraction is deterministic.
- **Polite by default**. Respects `robots.txt`, conservative concurrency,
  honest `User-Agent`.

See `CLAUDE.md` for the full design rules.

## Status

Phase 0 — scaffolding. See `plans.md`.

## License

Apache-2.0
