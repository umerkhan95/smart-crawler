# 02 — Adaptive Stopping ("when does the crawler have enough?")

Sources:
- <https://docs.crawl4ai.com/core/adaptive-crawling/>
- <https://docs.crawl4ai.com/advanced/adaptive-strategies/>
- <https://docs.crawl4ai.com/blog/articles/adaptive-crawling-revolution/>
- <https://docs.crawl4ai.com/blog/releases/0.7.0/>

The whole point of `smart_search` is to *not* crawl forever. This file
catalogs the stopping rules crawl4ai gives us for free, the math behind them,
and the alternatives we should keep in our back pocket.

## crawl4ai's three-layer score

`AdaptiveCrawler` computes a single `confidence ∈ [0,1]` from three components
recomputed after every page:

1. **Coverage** — fraction of query terms (or query embedding mass) present
   in the union of crawled pages. Statistical strategy: term frequency over
   query tokens. Embedding strategy: cosine coverage of `n_query_variations`
   expansions against the page embeddings.
2. **Consistency** — how coherent the collected facts are across pages.
   Statistical: distribution similarity of top terms. Embedding: pairwise
   similarity of selected chunks.
3. **Saturation** — rate of *new* unique terms / new embedding mass per
   additional page. The blog explicitly calls this "the most crucial metric."

Score is roughly `coverage * consistency * saturation_factor` (the docs
intentionally don't publish the exact formula; the source in
`crawl4ai/adaptive_crawler.py` is the ground truth if we ever need it).

## Stopping conditions (any one triggers)

| Trigger | Param | Default |
|---|---|---|
| Confidence reached | `confidence_threshold` | 0.7 |
| Page budget hit | `max_pages` | 20 |
| Diminishing returns | `min_gain_threshold` | 0.1 |
| No promising links left | (intrinsic) | — |

The "diminishing returns" rule is the only one that's actually adaptive — the
other three are just budgets. It compares the *expected* information gain of
the highest-scored next link against `min_gain_threshold`. If lower, stop.
Expected gain is estimated via the Scenting Algorithm: each candidate link's
anchor + URL + surrounding context is scored against the unmet portion of the
query, the top-k are explored, and the marginal gain is averaged.

### Confidence interpretation cheat sheet

| Range | Meaning |
|---|---|
| 0.0–0.3 | insufficient |
| 0.3–0.6 | partial |
| 0.6–0.7 | good |
| 0.7–1.0 | excellent |

## When the built-in stopping fails

1. **Sparse-fact queries** — "find the CEO of these 20 startups". Each
   answer is a single sentence, so saturation hits ~1.0 instantly and the
   crawler quits before visiting the actual `/about` page. The statistical
   strategy is especially weak here. Mitigation: use `BestFirstCrawlingStrategy`
   with a keyword scorer for the *navigation*, and only invoke
   `AdaptiveCrawler` for *open-ended* queries.
2. **High-noise sites** — boilerplate footers inflate coverage. Mitigation:
   wire `PruningContentFilter` into the markdown generator so adaptive sees
   `fit_markdown` only.
3. **Multi-entity queries** — "list all board members". Saturation can fire
   after one page that mentions two of seven members. Mitigation: drop the
   adaptive layer entirely, use a deterministic JsonCss schema once we know
   the listing page.
4. **Embedding drift** — semantic mode happily wanders into "related" pages
   that don't actually answer the query. Tighten `embedding_coverage_radius`
   (default 0.2) and raise `embedding_min_relative_improvement`.

## Alternatives (we should implement at least #1 and #4 ourselves)

1. **Coverage-based against an *expected schema*.** When the caller passes a
   Pydantic schema, "enough" = "every required field has at least one
   non-null value with a citation, for every requested entity." This is the
   smart-crawler-specific definition and should override anything crawl4ai
   computes. Track it in `pipeline.py`, not in the crawler.
2. **Confidence-based via per-field validators.** Score each extracted value
   with a Pydantic validator + a regex sanity check (price > 0, URL parses,
   email matches). Stop when mean per-field confidence exceeds threshold.
3. **Budget-based.** Hard caps from `Budget(max_pages, max_llm_calls,
   max_seconds)`. Always present as a backstop; never the *only* stop.
4. **Marginal-utility** (a la Anthropic research subagents,
   [`03_anthropic_multiagent_pattern.md`](03_anthropic_multiagent_pattern.md)):
   if the last N pages did not change *any* extracted record, stop. Cheap,
   robust, requires nothing from crawl4ai.
5. **Information-theoretic** (academic but interesting): treat extracted
   records as samples from a discrete distribution and stop when the entropy
   change per page < ε. Overkill for v1.

## Recommendation for smart-crawler

Use `AdaptiveCrawler` only as the *default discovery* engine for the
`summary` mode. For `structured` mode, drive the loop ourselves:

```
while not budget_exhausted:
    crawl_next_batch()
    extract_with_schema()
    if every_required_field_filled_with_citation():  # rule #1
        break
    if no_record_changed_in_last_N_pages():          # rule #4
        break
```

This keeps the stopping logic *in our code*, which is the only way to honour
CLAUDE.md's "schemas at every boundary" rule. Adaptive's confidence number
becomes one signal among several, not the gate.
