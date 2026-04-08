# 01 — crawl4ai API Surface (verified against v0.8.x docs)

**Current PyPI version:** `crawl4ai 0.8.6` (latest as of research date; v0.8.5 was the
"Anti-Bot Detection, Shadow DOM & 60+ Bug Fixes" milestone). Source:
<https://pypi.org/pypi/crawl4ai/json>. Our `pyproject.toml` currently pins
`crawl4ai>=0.4.0` — this is way too loose. Bump to `>=0.8.5,<0.9` before any
real coding; the AdaptiveCrawler API does not exist before 0.7.

All snippets below are copy-paste runnable against 0.8.x.

---

## 1. Core: `AsyncWebCrawler`, `BrowserConfig`, `CrawlerRunConfig`

Source: <https://docs.crawl4ai.com/core/browser-crawler-config/>

```python
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

browser = BrowserConfig(
    browser_type="chromium",      # chromium | firefox | webkit
    headless=True,
    viewport_width=1280, viewport_height=800,
    enable_stealth=False,         # anti-bot mode added in 0.8.5
    use_persistent_context=False,
    proxy_config=None,
    user_agent=None,
    verbose=False,
)

run = CrawlerRunConfig(
    cache_mode=CacheMode.BYPASS,  # BYPASS | ENABLED | READ_ONLY | WRITE_ONLY | DISABLED
    word_count_threshold=200,
    extraction_strategy=None,     # plug in JsonCss / LLM strategy here
    chunking_strategy=None,
    js_code=None,                 # str or list[str]
    wait_for=None,                # "css:.product" or "js:() => ..."
    page_timeout=60_000,
    scan_full_page=False,         # auto-scroll for lazy load
    screenshot=False, pdf=False,
    stream=False,                 # arun_many: yield as available
)

async with AsyncWebCrawler(config=browser) as crawler:
    result = await crawler.arun(url="https://example.com", config=run)
    # batch
    async for r in await crawler.arun_many(urls=[...], config=run.clone(stream=True)):
        ...
```

Both configs expose `.clone(**overrides)` which is the idiomatic way to derive
per-page variants without mutation. Use it heavily in `pipeline.py`.

---

## 2. AdaptiveCrawler

Source: <https://docs.crawl4ai.com/core/adaptive-crawling/>,
<https://docs.crawl4ai.com/api/adaptive-crawler/>,
<https://docs.crawl4ai.com/blog/releases/0.7.0/>

Introduced in **0.7.0** ("Adaptive Intelligence Update"). See
[`02_adaptive_stopping.md`](02_adaptive_stopping.md) for the full math
discussion; this section is just the API.

```python
from crawl4ai import AsyncWebCrawler, AdaptiveCrawler, AdaptiveConfig

cfg = AdaptiveConfig(
    confidence_threshold=0.7,        # stop when coverage*consistency*saturation >= this
    max_pages=20,
    top_k_links=3,                   # links followed per page (Scenting Algorithm)
    min_gain_threshold=0.1,          # stop if expected info gain < 10%
    strategy="statistical",          # "statistical" | "embedding" | "llm"
    save_state=False, state_path="state.json",
    # embedding-strategy knobs
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    embedding_llm_config=None,       # set to use API embeddings instead
    n_query_variations=10,
    embedding_coverage_radius=0.2,
    embedding_k_exp=3.0,
    embedding_min_relative_improvement=0.1,
    embedding_overlap_threshold=0.85,
)

async with AsyncWebCrawler() as crawler:
    adaptive = AdaptiveCrawler(crawler, config=cfg)
    state = await adaptive.digest(
        start_url="https://docs.python.org/3/",
        query="async context managers",
        resume_from=None,
    )
    adaptive.print_stats(detailed=True)
    pages = adaptive.get_relevant_content(top_k=5)  # [{url, score, content}]
    adaptive.export_knowledge_base("kb.jsonl")
```

`digest()` returns a state object whose key fields the `pages`, `confidence`,
and `metrics` history are exposed via the helper methods above. **Important
gotcha:** the LLM strategy is referenced in docs but undocumented; treat it as
experimental and stick to `statistical` (cheap, deterministic) or `embedding`
(better recall on fuzzy queries).

---

## 3. Deep crawl strategies

Source: <https://docs.crawl4ai.com/core/deep-crawling/>

```python
from crawl4ai.deep_crawling import (
    BFSDeepCrawlStrategy, DFSDeepCrawlStrategy, BestFirstCrawlingStrategy,
)
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from crawl4ai.deep_crawling.filters import (
    FilterChain, URLPatternFilter, DomainFilter,
    ContentTypeFilter, ContentRelevanceFilter, SEOFilter,
)

scorer = KeywordRelevanceScorer(keywords=["pricing", "ceo", "headquarters"], weight=0.7)

filters = FilterChain([
    URLPatternFilter(patterns=["*about*", "*team*", "*pricing*"]),
    DomainFilter(allowed_domains=["example.com"]),
    ContentTypeFilter(allowed_types=["text/html"]),
])

strategy = BestFirstCrawlingStrategy(
    max_depth=2,
    include_external=False,
    url_scorer=scorer,           # required for BestFirst
    max_pages=25,
    filter_chain=filters,
)

run = CrawlerRunConfig(deep_crawl_strategy=strategy, stream=True)
async for r in await crawler.arun("https://example.com", config=run):
    print(r.metadata["depth"], r.metadata["score"], r.url)
```

Common signature for all three (BFS / DFS / BestFirst):
`max_depth, include_external, max_pages, score_threshold, filter_chain,
url_scorer, resume_state, on_state_change, should_cancel`. Note `BestFirst`
**requires** a scorer. `BFS`/`DFS` accept one but it only re-orders the queue.

`prefetch=True` on `CrawlerRunConfig` is useful for **URL-only discovery** —
skips markdown/extraction and is what you want for cheap reconnaissance in
`probe.py`.

---

## 4. Extraction strategies

### JsonCssExtractionStrategy / JsonXPathExtractionStrategy

Source: <https://docs.crawl4ai.com/extraction/no-llm-strategies/>

```python
from crawl4ai import JsonCssExtractionStrategy

schema = {
    "name": "Products",
    "baseSelector": "div.product-card",
    "baseFields": [],                  # optional: fields read off the container itself
    "fields": [
        {"name": "title", "selector": "h2", "type": "text"},
        {"name": "price", "selector": ".price", "type": "text"},
        {"name": "url",   "selector": "a",   "type": "attribute", "attribute": "href"},
        {"name": "specs", "selector": ".spec", "type": "nested_list", "fields": [
            {"name": "key",   "selector": ".k", "type": "text"},
            {"name": "value", "selector": ".v", "type": "text"},
        ]},
    ],
}
strategy = JsonCssExtractionStrategy(schema, verbose=False)
```

Field `type`: `text | attribute | html | nested | nested_list | list`.
Result is a JSON string in `result.extracted_content`; `json.loads` it.

### LLMExtractionStrategy

Source: <https://docs.crawl4ai.com/extraction/llm-strategies/> + verified
against `crawl4ai/extraction_strategy.py` on GitHub.

```python
from crawl4ai import LLMExtractionStrategy, LLMConfig

llm = LLMExtractionStrategy(
    llm_config=LLMConfig(provider="openai/gpt-4o-mini",
                         api_token="env:OPENAI_API_KEY"),
    schema=Product.model_json_schema(),  # pydantic v2
    extraction_type="schema",            # or "block"
    instruction="Extract product objects with name and price.",
    chunk_token_threshold=1000,
    overlap_rate=0.1,
    apply_chunking=True,
    input_format="fit_markdown",         # markdown | html | fit_markdown
    force_json_response=False,
    verbose=False,
)
```

Real `__init__` signature (from source):
`llm_config, instruction, schema, extraction_type="block",
chunk_token_threshold, overlap_rate, word_token_rate, apply_chunking=True,
input_format="markdown", force_json_response=False, verbose=False, **kwargs`.
Legacy `provider/api_token/base_url/api_base` kwargs are deprecated — always
use `LLMConfig`.

**Critical finding for citations:** there is **no built-in grounding /
quote-tracking** in `LLMExtractionStrategy`. The class only tracks token
`usages` and `total_usage`. Smart-crawler's `citer.py` has to add provenance
itself by re-locating each extracted value back into the source markdown. See
[`04_citation_grounding.md`](04_citation_grounding.md).

### Schema generation (LLM-built CSS schemas)

Important and underdocumented: `JsonElementExtractionStrategy` (parent of the
JsonCss/JsonXPath strategies) exposes a static
`generate_schema(html, schema_type="CSS"|"XPATH", query, target_json_example)`
which uses an LLM to build a selector schema with a 3-round refinement loop.
This is the right primitive for `planner.py` — see
[`05_schema_inference.md`](05_schema_inference.md).

---

## 5. Content filters & markdown generator

Source: <https://docs.crawl4ai.com/core/markdown-generation/>

The Content Selection page does *not* document these; the markdown-generation
page does. Don't waste time on the former.

```python
from crawl4ai.content_filter_strategy import (
    PruningContentFilter, BM25ContentFilter, LLMContentFilter,
)
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

PruningContentFilter(threshold=0.5, threshold_type="fixed", min_word_threshold=50)
BM25ContentFilter(user_query="ceo headquarters", bm25_threshold=1.2,
                  language="english", use_stemming=True)
LLMContentFilter(llm_config=LLMConfig(provider="openai/gpt-4o-mini",
                                      api_token="env:OPENAI_API_KEY"),
                 instruction="Keep only paragraphs about leadership and offices.",
                 chunk_token_threshold=4096, verbose=False)

md_gen = DefaultMarkdownGenerator(
    content_filter=PruningContentFilter(threshold=0.6),
    content_source="cleaned_html",  # raw_html | cleaned_html | fit_html
    options={"ignore_links": False, "body_width": 0, "escape_html": False},
)
```

The generator produces **two** outputs that we will use heavily:

- `result.markdown.raw_markdown` — unfiltered
- `result.markdown.fit_markdown` — filtered (only when a content_filter is set)

Pass `fit_markdown` into `LLMExtractionStrategy(input_format="fit_markdown")`
to keep token bills small.

---

## 6. Dispatchers

Source: <https://docs.crawl4ai.com/advanced/multi-url-crawling/>

```python
from crawl4ai.async_dispatcher import (
    MemoryAdaptiveDispatcher, SemaphoreDispatcher, RateLimiter,
)

rate = RateLimiter(
    base_delay=(1.0, 3.0),       # randomised delay
    max_delay=60.0,
    max_retries=3,
    rate_limit_codes=[429, 503],
)

mem = MemoryAdaptiveDispatcher(
    memory_threshold_percent=85.0,
    check_interval=1.0,
    max_session_permit=10,
    memory_wait_timeout=600.0,
    rate_limiter=rate,
)

sem = SemaphoreDispatcher(max_session_permit=20, rate_limiter=rate)

async for r in await crawler.arun_many(urls=urls, config=run, dispatcher=mem):
    ...
```

Use `MemoryAdaptiveDispatcher` by default for bulk crawls. `SemaphoreDispatcher`
is for tests / predictable throughput.

---

## 7. Hooks

Hooks fire at well-defined lifecycle points on `AsyncWebCrawler.crawler_strategy`:

```python
async def on_page_context_created(page, **kwargs):
    await page.add_init_script("window.__SC=1;")
    return page

crawler.crawler_strategy.set_hook("on_page_context_created", on_page_context_created)
```

Available hook names (0.8.x):
`on_browser_created`, `on_page_context_created`, `before_goto`, `after_goto`,
`on_user_agent_updated`, `on_execution_started`, `before_retrieve_html`,
`before_return_html`. Use these for auth flows, cookie injection, custom
viewport, and dismissing cookie banners *before* extraction. Keep hook bodies
in a single `smart_crawler/hooks.py` so other modules don't import them.

---

## Version sensitivity flags

- `AdaptiveCrawler` / `AdaptiveConfig` — **0.7.0+ only**.
- `enable_stealth` on `BrowserConfig` — **0.8.5+**.
- `JsonElementExtractionStrategy.generate_schema` — present 0.6+, signature
  stabilised in 0.7.
- `BestFirstCrawlingStrategy` requires `url_scorer`; in older 0.5.x docs it
  was optional and silently degraded to BFS.
- `result.markdown.fit_markdown` — only populated if a `content_filter` was
  attached to the markdown generator. Easy to miss.
- `LLMConfig` is the only non-deprecated way to configure providers.
