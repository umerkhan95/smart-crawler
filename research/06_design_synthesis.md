# 06 — Design Synthesis: concrete module signatures

This file is the bridge from research to code. It proposes the function
signatures for every module in `plans.md` Phase 2, grounded in the findings
from files 01–05. Read those first.

All types reference `smart_crawler/types.py` (already in repo). Where
research suggests a new type, it's flagged with **NEW**.

---

## New types to add to `types.py`

```python
# NEW
class ExtractionPlan(BaseModel):
    """Output of planner.py — the recipe for one (query, domain) pair."""
    domain: str
    pydantic_model_spec: dict[str, Any]    # consumed by build_model()
    css_schema: dict[str, Any]             # crawl4ai JsonCss schema
    seed_urls: list[str]
    keyword_hints: list[str]               # for KeywordRelevanceScorer
    url_patterns: list[str]                # for URLPatternFilter
    notes: str = ""                        # LLM rationale, for debugging

class ProbeReport(BaseModel):
    """Output of probe.py — does the plan actually work on one page?"""
    url: str
    fields_found: dict[str, bool]          # per-field presence
    coverage: float                        # filled / total
    raw_extracted: dict[str, Any]
    error: str | None = None

class CrawlBatch(BaseModel):
    """Output of crawler.py — pages ready for extraction."""
    pages: list["RawPage"]
    pages_visited: int
    stopped_because: Literal[
        "budget", "saturation", "no_links", "schema_satisfied", "error"
    ]

class RawPage(BaseModel):
    url: str
    html: str
    fit_markdown: str
    fetched_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

class RouteDecision(BaseModel):
    """Output of router.py."""
    branch: Literal["snippet", "single_page", "deep_crawl", "adaptive_crawl"]
    rationale: str
    suggested_budget: Budget
```

`Fact`, `Source`, `Query`, `Result`, `Budget` already exist — keep them.

---

## Module signatures

All modules are **plain function modules**. No classes unless noted. None
of them import each other. `pipeline.py` is the only composer.

### `planner.py`

```python
async def make_plan(query: Query, sample_pages: list[RawPage]) -> ExtractionPlan: ...
```

Internally calls the LLM **at most twice**:
1. Pydantic model inference (research file 05, approach 1).
2. crawl4ai `JsonElementExtractionStrategy.generate_schema` for the CSS
   schema (research file 05, approach 2).

Caches by `sha256(query.query + domain)` on disk. Pure async, no globals.

### `probe.py`

```python
async def probe_plan(plan: ExtractionPlan, page: RawPage) -> ProbeReport: ...
```

Runs the plan's `css_schema` against one already-fetched page (no network)
and reports per-field hit rate. If `coverage < 0.5`, the caller should
reject the plan and re-plan. Zero LLM calls.

### `crawler.py`

```python
async def crawl(
    plan: ExtractionPlan,
    budget: Budget,
    mode: Literal["best_first", "adaptive"],
) -> CrawlBatch: ...
```

Two branches:
- `best_first` → `BestFirstCrawlingStrategy` + `KeywordRelevanceScorer`
  built from `plan.keyword_hints` + `URLPatternFilter` from
  `plan.url_patterns`. Used for *known-shape* extraction.
- `adaptive` → `AdaptiveCrawler` with `confidence_threshold=0.7`,
  `max_pages=budget.max_pages`. Used for *open-ended* `summary` mode.

Always uses `MemoryAdaptiveDispatcher`. Streams results so `pipeline.py`
can early-stop. Returns `stopped_because` so the caller knows whether to
retry. Zero LLM calls.

### `extractor.py`

```python
def extract(page: RawPage, css_schema: dict[str, Any]) -> list[dict[str, Any]]: ...
```

Pure function. Wraps `JsonCssExtractionStrategy` against the page's HTML
synchronously (the strategy itself is sync — only the crawler is async).
Returns raw dicts, no Pydantic validation yet (that happens in `citer.py`
after provenance is attached). Zero LLM calls.

### `repairer.py`

```python
async def repair(
    page: RawPage,
    plan: ExtractionPlan,
    failed_record: dict[str, Any],
) -> dict[str, Any] | None: ...
```

Called only when `extract()` returned `None`/empty for a page. Builds an
`LLMExtractionStrategy(input_format="fit_markdown")` with the
`pydantic_model_spec` schema and the explicit instruction to *return
`{value, quote}` per field* (research file 04). Returns the dict or `None`.
Failures must be loud — they bubble up to `pipeline.py` and increment
`Result.errors`. **Tagged `extracted_by="llm_fallback"`** by `citer.py`.
Bounded to 1 retry per page.

### `citer.py`

```python
def attach_citations(
    record: dict[str, Any],
    page: RawPage,
    extracted_by: Literal["deterministic", "llm_fallback"],
) -> Fact | None: ...
```

The grounding gate (research file 04). For deterministic records, builds a
`Source(url, retrieved_at, quote=matched_text)`. For llm_fallback records,
verifies each field's `quote` exists in `page.fit_markdown` (exact, then
fuzzy with rapidfuzz `partial_ratio >= 92`). Drops the record on failure
and returns `None` — the pipeline counts the drop as an error. **No
silent fallbacks**, per CLAUDE.md.

### `router.py`

```python
def route(query: Query) -> RouteDecision: ...
```

Pure function, no LLM, no I/O. Heuristic routing (research file 03,
lesson #3):
- Has the caller given specific URLs? → `single_page`
- Schema present + ≤5 entities? → `single_page` per entity
- Schema present + bulk job? → `deep_crawl` (best_first)
- No schema, broad question? → `adaptive_crawl`
- "What is X" / "define X" / one-shot fact? → `snippet` (cheapest)

Returns a `RouteDecision` with a derived `Budget` (smaller for snippet,
larger for adaptive).

### `pipeline.py`

```python
async def run(query: Query) -> Result: ...
```

The **only** module that imports its siblings. Composes:

```
1. decision = router.route(query)
2. plan     = await planner.make_plan(query, sample=await probe.fetch_seed(...))
3. report   = await probe.probe_plan(plan, sample_page)
   if report.coverage < 0.5: re-plan once, else fail loud
4. batch    = await crawler.crawl(plan, decision.suggested_budget, mode=...)
5. facts    = []
   for page in batch.pages:
       records = extractor.extract(page, plan.css_schema)
       if not records:
           record = await repairer.repair(page, plan, failed_record={})
           tag = "llm_fallback"
       else:
           record = records[0]; tag = "deterministic"
       fact = citer.attach_citations(record, page, tag)
       if fact: facts.append(fact)
6. validate facts against plan.pydantic_model_spec
7. return Result(query=query, facts=facts, pages_crawled=len(batch.pages),
                 llm_calls=accumulator, errors=...)
```

This is also where the schema-completeness early-stop lives (research file
02, recommendation): break out of the page loop once every required field
is filled with a citation.

---

## Where research suggests reconsidering CLAUDE.md

CLAUDE.md is mostly correct. Two narrow tensions:

1. **"<5 LLM calls per domain for bulk jobs"** — achievable but only just.
   Budget is: 1 (Pydantic infer) + 1 (CSS schema gen) + ≤2 (repairer
   retries on bad pages) + 0 (crawler) = 4. Anthropic's data
   ([`03_anthropic_multiagent_pattern.md`](03_anthropic_multiagent_pattern.md)
   #2) suggests when token spend correlates 80% with quality, *capping
   too aggressively hurts*. Recommendation: keep the soft target but make
   the actual cap a `Budget.max_llm_calls` field (already exists) and let
   callers dial it up for high-value queries. The rule should be a
   *default*, not a wall.

2. **"Modules do not import each other laterally"** — agreed, but the
   `Fact / Source / Page` types in `types.py` *are* imported laterally.
   That's fine — `types.py` is a leaf with no dependencies. Worth saying
   so explicitly in CLAUDE.md to avoid future confusion: "leaf type
   modules are exempt; behaviour modules are not."

3. **"Bulk extraction is deterministic (CSS/XPath)"** — true for the
   happy path, but research file 04 forces LLM use whenever a CSS path
   misses *and* `must_cite=True` requires verification. Add a sentence:
   "LLM fallback through `repairer.py` is permitted but must be tagged
   and counted." (CLAUDE.md already says "tagged" — just make explicit
   that `repairer.py` is the *only* module allowed to do it.)

Nothing in research contradicts the SRP / no-cross-imports / Pydantic-at-
boundaries / fail-loud rules. Those stand.

---

## Implementation order (proposed)

1. `types.py` additions (ExtractionPlan, ProbeReport, CrawlBatch, RawPage,
   RouteDecision)
2. `router.py` (pure logic, easiest, gives shape to the pipeline)
3. `extractor.py` + `citer.py` (deterministic path; testable without
   network using fixture HTML)
4. `crawler.py` (best_first only at first; adaptive in a second pass)
5. `probe.py`
6. `planner.py` (the only LLM-heavy module)
7. `repairer.py`
8. `pipeline.py` — wires it together
9. `api.py` — replace `NotImplementedError` with `pipeline.run(...)`

Tests written before each module per CLAUDE.md "unit tests per module".
