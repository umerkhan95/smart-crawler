# 04 — Adaptive Stop Conditions for Agentic Crawling / Research (2025-2026)

## The four paradigms in the wild

1. **Information-gain saturation.** Track novel terms / novel embeddings per new page; stop when gain < threshold. This is **Crawl4AI AdaptiveCrawler's** model: Coverage × Consistency × Saturation, with `min_gain_threshold=0.1`, `confidence_threshold=0.7`, `max_pages=20` defaults ([Crawl4AI adaptive-crawling docs](https://docs.crawl4ai.com/core/adaptive-crawling/), [v0.7 release notes](https://docs.crawl4ai.com/blog/releases/0.7.0/)). Crawl4AI explicitly positions this as *"information foraging"* borrowed from Pirolli & Card's HCI work.
2. **Schema-completeness.** Stop when the target Pydantic model's required fields are all filled. This is the **LlamaIndex / Instructor / BAML** pattern for structured extraction and what smart-crawler is committing to.
3. **Confidence-thresholding.** The planner LLM self-scores "am I done?" and stops when >X. Used by **Perplexity Deep Research** (3-5 sequential refinement passes, confidence ratings "high/medium/uncertain") and **OpenAI Deep Research** (low-confidence ⚠️ flags) ([Perplexity](https://www.perplexity.ai/hub/blog/introducing-perplexity-deep-research), [Helicone](https://www.helicone.ai/blog/openai-deep-research)).
4. **Budget-only.** Fixed cap on pages/queries/tokens. **GPT Researcher** and **Tavily** default to this: GPT Researcher's planner fans out a fixed set of sub-queries, budget ~$0.10/research, ~3 minutes ([GPT Researcher GitHub](https://github.com/assafelovic/gpt-researcher), [Tavily docs](https://docs.tavily.com/examples/open-sources/gpt-researcher)). **Anthropic's multi-agent system** also uses budget-and-count caps — they explicitly cite "orchestrator spawning 50 agents for simple questions" as a failure they hardcoded against ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)).

## Is there a published comparison?

**Effectively no.** The closest thing is Carnegie Mellon's **DeepResearchGym** (May 2025), which benchmarked GPT Researcher, Perplexity, OpenAI Deep Research, OpenDeepSearch, and HuggingFace agents on 1,000 complex queries. GPT Researcher won on citation quality, report quality, and coverage — but the benchmark measured *output quality*, not *stop-condition efficiency*, and did not isolate the stop rule as a variable. There is no head-to-head "saturation vs schema vs confidence" comparison in the literature as of early 2026.

This is a real gap. It also means **any claim smart-crawler makes about its stop rule being better has to be defended on its own benchmark**, not by citation.

## What production systems actually use

- **Crawl4AI**: hybrid saturation + budget. Default pattern.
- **LlamaIndex agentic retrieval**: schema-completeness + a token budget. LlamaIndex Workflows default to stateless stop-on-output.
- **LangChain's research agents (open_deep_research)**: confidence-thresholded planner + hard iteration cap.
- **GPT Researcher**: planner decomposes into fixed N sub-queries, no adaptive stopping within a sub-query — purely budget.
- **Tavily**: per-query result count caps; their `search_depth="advanced"` triples the result budget.
- **Perplexity Deep Research**: 20-50 parallel queries + 3-5 sequential refinements, adaptive on "what data is missing" judgment.

Notable: **no production system combines schema-completeness with saturation**, which is what smart-crawler proposes. That is either a novel contribution or a sign that nobody else found it useful.

## The hidden disagreement

Crawl4AI's saturation metric treats "novel terms" as a proxy for "novel information." This is *hand-wavy* — a page can introduce novel terms that are all boilerplate (footer legalese, related-article snippets), exactly the slop smart-crawler is trying to avoid. Saturation on noisy HTML and saturation on `fit_markdown` would give different answers, and crawl4ai does not document which one it uses consistently across versions.

Schema-completeness is cleaner: you either have the field filled with a verified quote or you don't. But schema-completeness does not naturally handle `summary` mode where there is no schema.

## Implications for smart-crawler

smart-crawler's two-mode split is *correct* but under-defended:
- **Structured mode**: schema-completeness stop (aligned with LlamaIndex/Instructor).
- **Summary mode**: defers to crawl4ai's AdaptiveCrawler saturation.

**Risk flag (high):** the architectural rule "schema-completeness drives the stop loop, NOT crawl4ai's saturation metric" in issue #2 is defensible for structured mode but leaves summary mode running on crawl4ai's saturation, which has not been independently validated. Summary mode is the most exposed to the saturation-on-noisy-HTML problem.

**Novelty flag:** smart-crawler is the first OSS library I found that explicitly combines schema-completeness + budget + (inherited) saturation as a three-condition OR stop rule. That is a genuine, if small, contribution — worth calling out in the README.

**Biggest unknown:** no one in the field has a published answer to "when has a research agent done enough?" smart-crawler has to invent its own defense.

## Sources

- [Crawl4AI — Adaptive Crawling docs](https://docs.crawl4ai.com/core/adaptive-crawling/)
- [Crawl4AI v0.7.0 release notes](https://docs.crawl4ai.com/blog/releases/0.7.0/)
- [Anthropic — How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [GPT Researcher GitHub](https://github.com/assafelovic/gpt-researcher)
- [Tavily docs — GPT Researcher example](https://docs.tavily.com/examples/open-sources/gpt-researcher)
- [Perplexity Deep Research blog](https://www.perplexity.ai/hub/blog/introducing-perplexity-deep-research)
- [LangChain open_deep_research](https://github.com/langchain-ai/open_deep_research)
- [Helicone — OpenAI Deep Research analysis](https://www.helicone.ai/blog/openai-deep-research)
