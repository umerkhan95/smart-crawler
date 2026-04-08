# 08 — OSS Landscape Feature Matrix (2025-2026)

## The matrix

| Project | Stateless? | Built-in grounding? | Schema enforcement | Auto schema gen | Router / difficulty | License | GitHub stars (approx, 2026) | Primary framing |
|---|---|---|---|---|---|---|---|---|
| **crawl4ai** (unclecode) | Yes (library) | **No** | Yes (JsonCssExtractionStrategy + Pydantic) | Yes (generate_schema) | Partial (Adaptive vs BestFirst) | Apache-2.0 | ~58k+ | LLM-friendly crawler, markdown-first |
| **LangExtract** (Google) | Yes | **Yes** (char offsets) | Yes (Gemini-driven) | Partial (prompt-specified) | No | Apache-2.0 | Mid-tier (July 2025 release) | Extraction with source grounding from already-clean text |
| **Firecrawl** (Mendable) | Yes (API) | No | Yes (`/extract` endpoint) | Partial | No | AGPL-3.0 + hosted | ~30k+ | API-first crawler → clean Markdown |
| **ScrapeGraphAI** | Yes (per call) | No (LLM-validated, not quote-grounded) | Yes (Pydantic) | Yes (prompt-based) | Partial (graph selection) | MIT | ~15k+ | Prompt → structured JSON via LLM-graph |
| **llm-scraper** (TS) | Yes | No | Yes (Zod) | Via prompt | No | MIT | ~2k+ | TypeScript Playwright + LLM |
| **Apify** | No (platform, stateful) | No | Yes | Yes | Yes (actors) | Commercial / Apache-2.0 SDK | 5k SDK | SaaS scraping platform |
| **Browse.ai** | No | No | Yes (point-and-click) | Via UI | No | Commercial | N/A | No-code robot training |
| **RAGFlow** | No (server) | Partial (references in chunks) | No (doc-focused) | N/A | No | Apache-2.0 | ~40k+ | RAG engine with deep doc understanding |
| **Reader (Jina)** | Yes (API) | No | No | No | No | Apache-2.0 | ~8k+ | URL → clean LLM-ready Markdown |
| **Trafilatura** | Yes | No | No | No | No | Apache-2.0 | ~4k+ | Main-content extraction, classical |
| **Markdownify / markdown-it** | Yes | No | No | No | No | MIT | N/A | HTML → MD conversion |
| **GPT Researcher** | Yes (per run) | Partial (cites sources in report) | No | No | Yes (planner) | MIT/Apache | ~17k+ | Full research agent, not library |

Star counts are rough 2026 estimates cross-referenced from Firecrawl's and Apify's "best of" lists and GitHub badges; precise counts drift weekly ([Firecrawl best OSS crawlers 2026](https://www.firecrawl.dev/blog/best-open-source-web-crawler), [6 OSS AI crawler comparison](https://liduos.com/en/ai-develope-tools-series-3-open-source-ai-web-crawler-frameworks.html), [Capsolver Crawl4AI vs Firecrawl](https://www.capsolver.com/blog/AI/crawl4ai-vs-firecrawl)).

## Is smart-crawler filling a real gap?

**Yes — partially.** The honest breakdown:

### What crawl4ai already does (~60% of smart-crawler's scope)
- Adaptive + best-first crawling strategies
- `PruningContentFilter` + `BM25ContentFilter` (slop removal)
- `JsonCssExtractionStrategy.generate_schema()` (LLM-inferred schemas)
- `MemoryAdaptiveDispatcher`, robots.txt, concurrency
- Stateless library form

**Crawl4ai is smart-crawler's biggest overlap. Issue #2 explicitly acknowledges this — smart-crawler is a thin orchestration layer on top of crawl4ai, not a replacement.**

### What LangExtract already does (~20% of smart-crawler's scope)
- Quote-level grounding with exact character offsets
- But: operates on already-clean text, not live web scraping

### What Firecrawl already does
- Fetching + Markdown conversion + `/extract` endpoint
- But: AGPL, no verbatim quote grounding, no stop-condition orchestration

### The genuine gap smart-crawler fills
What **no single OSS library ships today** is all four of these combined:
1. **Verbatim quote grounding over scraped HTML** (LangExtract has it but not for live crawls; crawl4ai has no grounding at all).
2. **Schema-completeness as a stop rule** for crawling (crawl4ai uses saturation, not schema).
3. **LLM-as-planner, deterministic-as-extractor** separation with strict allowed-LLM-call accounting (nobody markets this as a rule).
4. **Prompt-injection-aware boundary** where the caller's reasoning LLM never sees raw HTML (no OSS library frames itself this way).

Individually, each of these is 50-80% solved by existing tools. Combined, *nobody* ships them. The gap is real but *narrow*: smart-crawler is an opinionated composition, not a novel algorithm.

## Brutally honest take

**crawl4ai already does ~60% of what smart-crawler proposes.** The remaining 40% is:
- A citer/grounding module (the keystone, genuinely missing)
- A stricter stop rule
- An opinionated LLM-call budget
- Threat-model-aware HTML sanitization

This is a **wrapper library with an opinionated posture**, not a from-scratch contribution. That is fine — the React ecosystem is built on opinionated wrappers — but the marketing should be honest: **"the grounding + discipline layer crawl4ai intentionally doesn't ship"**, not "the first AI-safe crawler."

The risk: if crawl4ai ships a citer module in v0.9, 40% of smart-crawler's differentiation evaporates overnight. It is worth checking the crawl4ai roadmap and GitHub issues periodically.

ScrapeGraphAI is a different posture (LLM-as-extractor, no quote grounding, MIT) and is not a direct overlap. Firecrawl is AGPL, which is a real license barrier for commercial users — smart-crawler (Apache, presumably) has a legitimate licensing gap to fill alone.

## Implications

**Risk flag (high):** crawl4ai adding a grounding module (plausible, since LangExtract made it table stakes) would cut smart-crawler's differentiation in half. Mitigate by:
1. Shipping the citer + benchmark as the headline contribution.
2. Upstreaming the grounding ideas to crawl4ai if they want them (turns a threat into a co-op).

**Novelty flag:** "opinionated composition with grounding + schema-stop + injection-boundary" is a legitimate novel *recipe*, even if each ingredient exists. The benchmark and the threat-model framing are where originality will actually be recognized.

**Verdict:** real gap, narrow, defensible only with a rigorous benchmark and honest marketing. If the README overclaims, the project will be ignored by both sides (crawl4ai users see overlap, LangExtract users see missing features).

## Sources

- [Firecrawl — Best OSS crawlers 2026](https://www.firecrawl.dev/blog/best-open-source-web-crawler)
- [Firecrawl — Best web extraction tools 2026](https://www.firecrawl.dev/blog/best-web-extraction-tools)
- [Capsolver — Crawl4AI vs Firecrawl](https://www.capsolver.com/blog/AI/crawl4ai-vs-firecrawl)
- [Brightdata — Crawl4AI vs Firecrawl](https://brightdata.com/blog/ai/crawl4ai-vs-firecrawl)
- [Liduos — 6 OSS AI crawler frameworks compared](https://liduos.com/en/ai-develope-tools-series-3-open-source-ai-web-crawler-frameworks.html)
- [ScrapeGraphAI vs Firecrawl](https://scrapegraphai.com/blog/scrapegraph-vs-firecrawl)
- [Google LangExtract GitHub](https://github.com/google/langextract)
- [unclecode/crawl4ai GitHub](https://github.com/unclecode/crawl4ai)
