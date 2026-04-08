# 09 — Aggressive Synthesis: Is smart-crawler Aligned with SOTA?

Per-topic verdicts, then three blunt final calls.

---

## 1. Orchestrator + Sub-agent Pattern

**Current SOTA.** Anthropic's 2025 multi-agent research post is the canonical pro-pattern reference; Cognition's "Don't Build Multi-Agents" is the canonical contrarian. The reconciliation (LangChain, Phil Schmid, Cemri et al. arXiv:2503.13657 with 41-86.7% failure rates) is: the pattern works for *parallel read-only retrieval sub-tasks* that return artifacts, fails for *collaborative decision-making* sub-tasks.

**smart-crawler's choice.** Single orchestrator dispatching deterministic workers via fixed DAG; exactly 1-2 LLM calls (planner + optional repairer); no agents talk to each other.

**Verdict.** ✅ ALIGNED — the safe side of the debate.
**Confidence.** High.
**Risk if wrong.** Minimal; the architecture sidesteps Cognition's critique entirely because sub-components are pure functions, not agents.
**Action.** Ship-as-is. Do not add parallel LLM planners later.

---

## 2. Citation Grounding / Quote-Span Verification

**Current SOTA.** Verbatim quote-span grounding is the convergent standard as of 2025 — Google LangExtract (character offsets), Anthropic Citations API (sentence spans), ReClaim, LAQuer, Vectara HHEM all point the same direction. The open debate is only about granularity.

**smart-crawler's choice.** `citer.py` attaches `{url, quote, retrieved_at}` per record; exact match then `rapidfuzz.partial_ratio >= 92` fallback.

**Verdict.** ✅ ALIGNED, with one 🎯 NOVEL angle — smart-crawler grounds against *noisy scraped HTML*, not clean document text. No SOTA tool does that today.
**Confidence.** High on the direction, medium on the fuzzy threshold.
**Risk if wrong.** A permissive 92-threshold silently reintroduces the hallucinations the layer exists to prevent.
**Action.** Instrument-and-measure. Calibrate the 92 threshold against HHEM on the golden set before declaring it final.

---

## 3. Schema-Driven vs LLM-as-Extractor

**Current SOTA.** "LLM as compiler, not runtime." Every production-serious framework (crawl4ai, ScrapeGraphAI caching mode, GroupBWT's DataOps guidance) uses LLMs *once* to generate a deterministic extractor. Cost gap is ~3 orders of magnitude, unchanged in 2026.

**smart-crawler's choice.** `planner.py` (LLM once) → `extractor.py` (deterministic) → `repairer.py` (LLM only on extractor failure).

**Verdict.** ✅ ALIGNED — textbook 2025 pattern.
**Confidence.** High.
**Risk if wrong.** Single-shot schema inference fails on narrative pages; `probe.py`'s coverage floor is the mitigation but unvalidated.
**Action.** Ship-as-is, but the golden set **must** include narrative pages, not just catalogs, or the benchmark overstates the win.

---

## 4. Adaptive Stop Conditions

**Current SOTA.** No field-level consensus. Four paradigms (saturation, schema-completeness, confidence, budget) in production, no published head-to-head comparison. DeepResearchGym (CMU, May 2025) benchmarks output quality but does not isolate the stop rule.

**smart-crawler's choice.** Schema-completeness for structured mode; crawl4ai's saturation for summary mode; budget as hard cap on both.

**Verdict.** 🎯 NOVEL (combining schema + saturation + budget is uncommon) / ⚠️ DIVERGES from crawl4ai's default in structured mode.
**Confidence.** Medium — the field has no benchmark, so "SOTA" is a moving target.
**Risk if wrong.** Summary mode leans entirely on crawl4ai's saturation metric, which is saturation-on-noisy-HTML and has no independent validation.
**Action.** Instrument-and-measure. Publish a stop-condition ablation as part of the benchmark — this alone is publishable content.

---

## 5. Token-Noise Quantification

**Current SOTA.** No standard benchmark exists. RAGAS Context Precision is the closest proxy; RULER / LongBench v2 measure model noise-tolerance, not retrieval cleanliness; HHEM measures downstream hallucination. No public web-retrieval corpus with gold spans.

**smart-crawler's choice.** Claims ≥40% token-noise reduction. Methodology not yet defined.

**Verdict.** 🚨 BEHIND (as currently specified). The claim is unfalsifiable without a custom harness.
**Confidence.** High — I am confident the claim as written cannot be defended.
**Risk if wrong.** Reviewers dismiss the headline metric on contact; the README's credibility collapses.
**Action.** **Redesign the claim before shipping.** Must define: (a) golden set, (b) quality-preservation metric (RAGAS faithfulness or HHEM), (c) statistical test, (d) reproducible harness. The benchmark and its methodology are *more valuable than the library* — make that the headline contribution.

---

## 6. Stateless vs Stateful

**Current SOTA.** Both are mainstream. LangGraph is the stateful champion; LlamaIndex Workflows, crawl4ai, Firecrawl, GPT Researcher are stateless. Production teams hybridize (LlamaIndex retrieval + LangGraph orchestration). "No cache, no DB" is a legitimate library-posture choice, not a foot-gun.

**smart-crawler's choice.** Fully stateless; CLAUDE.md forbids cache entirely.

**Verdict.** ✅ ALIGNED on statelessness, ⚠️ DIVERGES on the absolute cache ban.
**Confidence.** High.
**Risk if wrong.** Every re-run on the golden set re-fetches every page (benchmark repeatability and cost foot-gun); power users will fork to add caching.
**Action.** Soften the rule: "no implicit state; optional caller-provided cache backend." Same architectural purity, no foot-gun. `cache: CacheBackend | None = None` as a parameter.

---

## 7. Indirect Prompt Injection

**Current SOTA.** OWASP LLM01:2025 is the reference. Microsoft Spotlighting (datamarking / encoding) is the deployed defense; Tool Result Parsing (arXiv:2601.04795, 2026) is essentially smart-crawler's architecture in paper form; 5-document 90% RAG poisoning attacks are public.

**smart-crawler's choice.** Implicit schema-boundary defense; no explicit sanitization mentioned in issue #2.

**Verdict.** 🎯 NOVEL on architecture (the schema boundary is a legitimate defense nobody markets), 🚨 BEHIND on implementation (planner.py receives raw HTML — high-value attack surface).
**Confidence.** High.
**Risk if wrong.** A corrupted planner schema contaminates the entire crawl for a domain — attacker's reward is huge relative to attack cost.
**Action.** **Redesign planner input path** before shipping: strip scripts/comments/iframes/meta/noscript/zero-width, apply datamarking spotlighting, schema-sanity-check the planner output, log prompts for forensics. Then market the injection resistance as a first-class feature.

---

## 8. OSS Landscape Gap

**Current SOTA.** crawl4ai covers ~60% of smart-crawler's scope; LangExtract covers grounding on clean text; Firecrawl covers fetching + Markdown + extract endpoint (AGPL). No single library combines grounding + schema-stop + injection boundary.

**smart-crawler's choice.** Thin opinionated composition layer on top of crawl4ai + Pydantic + Gemini/Claude.

**Verdict.** ⚠️ DIVERGES on novelty claims — it is a recipe, not a new algorithm. Real but *narrow* gap.
**Confidence.** High.
**Risk if wrong.** If crawl4ai ships a citer module in v0.9, 40% of the differentiation evaporates.
**Action.** Ship-as-is on architecture; **rewrite the README marketing** to be honest: *"the grounding + discipline layer crawl4ai intentionally doesn't ship."* Monitor crawl4ai roadmap. Consider upstreaming.

---

## Three Blunt Final Verdicts

### Should this project exist? — **Yes, as a benchmark-first project, not a library-first project.**

The library is a reasonable opinionated wrapper. It would be one of dozens. What is *actually* missing from the field is a rigorous, open, reproducible **benchmark for web-retrieval noise** with quality-preservation guardrails. No such benchmark exists (topic #5). Shipping that benchmark alongside a reference implementation (the library) is a legitimate contribution. Shipping the library without the benchmark is noise — there are already enough wrappers.

**Pivot recommendation:** frame smart-crawler primarily as *"the first open benchmark for LLM web-retrieval noise, plus a reference implementation that scores well on it."* The library is the existence proof; the benchmark is the product.

### What's the biggest risk? — **The ≥40% token-noise claim is unfalsifiable as currently written.**

The single most attackable claim in the whole project is the headline number, and the methodology does not yet exist to defend it. This is a career/reputation risk disproportionate to the library's other concerns. Any reviewer who has read a RAGAS or HHEM paper will ask "40% vs what, measured how, at what quality level?" and if the README cannot answer in one screen, the project is dismissed. Fix the benchmark before the library.

Secondary risk: crawl4ai adding native grounding in v0.9 eating the differentiation — mitigated by speed to market and benchmark ownership.

### What's the most novel contribution if we ship? — **Verbatim quote grounding over noisy scraped HTML, inside a schema-boundary that resists indirect prompt injection.**

Not the benchmark (important but a methodology contribution), not the orchestration (wrapper around crawl4ai), not statelessness (common). The *technical* novelty that nobody else ships is the combination of: (a) extract-and-ground from live, hostile HTML, (b) verbatim quote verification that survives DOM noise, (c) an architectural boundary the caller's reasoning LLM cannot be tricked across because it literally never sees raw HTML. LangExtract has grounding but only on clean text. crawl4ai has noisy HTML but zero grounding. Nobody bridges the two. That bridge is the novel contribution — everything else supports it.

If the project ships one thing well, ship that.
