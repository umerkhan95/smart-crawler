# 03 — Schema-Driven vs LLM-as-Extractor (2025-2026)

## Where the trend is actually going

Two trends are happening simultaneously and they contradict the naive "LLMs got cheaper so just use LLMs" narrative:

1. **LLM extraction is winning on heterogeneous / layout-shifting pages** because models now tolerate DOM drift that breaks CSS selectors. ScrapeGraphAI, Firecrawl's `extract`, llm-scraper, and Apify's AI Scrapers are all LLM-first.
2. **Deterministic extraction is winning on high-volume, structured commerce / catalog / listing pages** because the unit economics are still crushingly in favor of CSS/XPath at scale.

## The numbers

The best-public head-to-head numbers I found (2025-2026):

| Metric | CSS/XPath | LLM extraction |
|---|---|---|
| Accuracy on stable pages | ~100% (but 0% when DOM drifts) | 95-98% typically; 98.4-100% reported on 3,000-page eval with stable schemas |
| Cost per 1M pages | $1–$5 | $666–$3,025 (depending on model) |
| Per-request | ~$0 | $0.001–$0.01 |
| Numerical-precision failures | None | Frequent (VAT inclusive/exclusive, currency, unit vs total) |
| Resilience to DOM change | None | High (semantic reasoning) |

Sources: Apify 2026 AI web scraping report ([Apify blog](https://use-apify.com/blog/web-scraping-with-ai-llms-2026)), GroupBWT LLM-for-web-scraping analysis ([groupbwt.com](https://groupbwt.com/blog/llm-for-web-scraping/)), Scrapfly's Crawl4AI explainer ([Scrapfly](https://scrapfly.io/blog/posts/crawl4AI-explained)), Crawl4AI's own LLM-Free Strategies docs ([crawl4ai docs](https://docs.crawl4ai.com/extraction/no-llm-strategies/)).

The cost gap is **roughly 3 orders of magnitude**. That has not closed in 2025-2026 despite gpt-4o-mini and Claude Haiku getting cheaper, because deterministic extraction cost is essentially *bandwidth + CPU*, not inference.

## What production teams actually do

The consensus across the ScrapeGraphAI, Firecrawl, and Apify write-ups is **hybrid**: use LLMs *once* to infer a CSS/XPath schema from sample pages, then run the deterministic schema at scale, falling back to LLM only on pages where the deterministic schema fails to hit coverage. This is exactly crawl4ai's `JsonElementExtractionStrategy.generate_schema()` pattern ([Crawl4AI LLM-free strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)). It is also what GroupBWT recommends for "DataOps at scale" ([groupbwt.com](https://groupbwt.com/blog/llm-for-web-scraping/)).

DEV.to's "The End of Selectors" is the loudest contrarian voice claiming selectors are obsolete ([dev.to](https://dev.to/deepak_mishra_35863517037/the-end-of-selectors-llm-driven-html-parsing-28b2)), but it does not provide cost numbers and is explicitly for low-volume use. No credible production source I found claims "use LLMs for everything" at scale.

The harder-to-find disagreement: **How reliable is LLM-generated CSS schema on the first shot?** crawl4ai's own docs acknowledge that generated schemas work well on pages with repeating structure (listings, catalogs) and poorly on narrative pages. There is no public benchmark of `generate_schema()` accuracy that I could find, which is a gap smart-crawler's `probe.py` coverage gate is well-positioned to address.

## Is the trend "more LLM" or "more deterministic"?

It is **"LLM as compiler, not runtime"** — LLMs generate the extractor; the extractor runs deterministically. Every serious OSS tool (crawl4ai, llm-scraper, ScrapeGraphAI's SmartScraper caching mode) has converged on this. Naive "send every page to GPT-4" is treated as a starter pattern, not a production one.

## Implications for smart-crawler

smart-crawler's `planner.py` → `extractor.py` split (LLM infers CSS schema once, deterministic extraction runs on every page, `repairer.py` LLM-fallback only when `citer.py` rejects a record) is **textbook 2025 SOTA**. It is the pattern GroupBWT, crawl4ai, and Apify independently recommend, and it correctly captures the 3-orders-of-magnitude cost asymmetry.

**Risk flag:** single-LLM-call schema inference fails on narrative-heavy pages (news articles, blog posts, forum threads). The `probe.py` coverage-floor gate (if `coverage < 0.5`, re-plan once then fail loud) is the right mitigation but has not been validated. The golden set *must* include narrative pages, not just listings/catalogs, or the benchmark will overstate smart-crawler's deterministic-extraction win rate.

**No divergence from field.** smart-crawler is doing the consensus thing.

## Sources

- [Apify — Web Scraping with AI 2026](https://use-apify.com/blog/web-scraping-with-ai-llms-2026)
- [GroupBWT — LLM for Web Scraping](https://groupbwt.com/blog/llm-for-web-scraping/)
- [Crawl4AI — LLM-Free Strategies docs](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
- [Scrapfly — Crawl4AI Explained](https://scrapfly.io/blog/posts/crawl4AI-explained)
- [ScrapeGraphAI — LLM Web Scraping](https://scrapegraphai.com/blog/llm-web-scraping)
- [DEV — The End of Selectors](https://dev.to/deepak_mishra_35863517037/the-end-of-selectors-llm-driven-html-parsing-28b2)
- [StructEval — arXiv:2505.20139](https://arxiv.org/html/2505.20139v1)
