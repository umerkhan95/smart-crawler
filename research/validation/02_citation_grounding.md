# 02 — Citation Grounding and Quote-Span Verification (2025-2026)

## What the field does today

**Verbatim quote-span grounding is, as of 2026, the de facto gold standard** for production systems that care about auditability. The three most-cited references:

1. **Google LangExtract (July 2025)** — every extracted entity is mapped to exact *character offsets* in the source text, visualizable in HTML. Google explicitly positions this as traceability-first extraction ([Google Developers blog](https://developers.googleblog.com/introducing-langextract-a-gemini-powered-information-extraction-library/), [GitHub](https://github.com/google/langextract)).
2. **Anthropic Citations API (Jan 2025, GA)** — the server chunks documents into sentences and returns `cited_text` spans per claim. Anthropic reports citations improved recall accuracy up to 15% over prompt-based citation in internal evals; notably, `cited_text` does *not* count against output tokens, explicitly pricing grounding in ([Anthropic announcement](https://www.anthropic.com/news/introducing-citations-api), [Simon Willison analysis](https://simonwillison.net/2025/Jan/24/anthropics-new-citations-api/), [Claude docs](https://platform.claude.com/docs/en/build-with-claude/citations)).
3. **Vectara HHEM-2.3 leaderboard (2025 refresh, 7,700 articles across law/medicine/finance)** — the public standard for measuring *post-hoc* hallucination in summarization. Hallucination is scored 0-1 against verbatim grounding ([Vectara blog](https://www.vectara.com/blog/introducing-the-next-generation-of-vectaras-hallucination-leaderboard), [GitHub](https://github.com/vectara/hallucination-leaderboard)).

## The academic line

Bohnet et al. "Attributed Question Answering" (arXiv:2212.08037) is still the foundational framing. Its 2024-2025 descendants:

- **"Attribute First, Then Generate"** (ACL 2024) — content-selection *before* generation produces more concise, more accurate citations ([ACL Anthology](https://aclanthology.org/2024.acl-long.182/)).
- **ReClaim** (arXiv:2407.01796, 2024-2025) — interleaved reference-and-claim generation, reports ~90% citation accuracy on long-form QA ([arXiv](https://arxiv.org/abs/2407.01796)).
- **LAQuer** (ACL 2025) — localized attribution queries, lets users request provenance for arbitrary output spans rather than pre-fixed sentence boundaries ([arXiv:2506.01187](https://arxiv.org/pdf/2506.01187)).

Direction of travel: the field is moving from *post-hoc faithfulness metrics* (RAGAS faithfulness, HHEM) toward **generation-time locally-attributable spans** ([LAQuer](https://aclanthology.org/2025.acl-long.746.pdf)). The research community considers post-hoc hallucination scoring a stopgap; in-place quote attachment is the preferred architecture.

## Has the field "moved on" from verbatim quotes?

No. If anything, it has doubled down. Both Google (LangExtract character offsets) and Anthropic (Citations API sentence chunks) landed on near-identical designs in the same 6-month window, which is as close to convergent evolution as you get in ML tooling. RAGAS's `faithfulness` metric also decomposes answers into claims and checks each claim against retrieved context — same spirit, coarser grain ([RAGAS docs](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/)).

The one contested area is *granularity*: character offsets (LangExtract), sentence spans (Anthropic), or sub-sentence claim chunks (ReClaim). No consensus — LAQuer's pitch is exactly that granularity should be query-dependent.

## Implications for smart-crawler

smart-crawler's `citer.py` "every returned fact carries `{url, quote, retrieved_at}`, ungrounded facts are dropped" is **aligned with SOTA**. The design choice to use exact match then `rapidfuzz.partial_ratio >= 92` as fallback is defensible — LangExtract uses exact offsets, but LangExtract receives clean text; for LLM-extracted facts from noisy HTML, fuzzy fallback is a reasonable compromise also used by Vectara's open HHEM variants.

**Risk flag:** the 92 threshold is picked from hip-pocket intuition; it is not backed by any published study in the research file 04. Worth empirically calibrating against HHEM on the golden set, because a too-permissive threshold silently reintroduces the hallucinations the layer is supposed to stop.

**Novelty flag:** most SOTA grounding tools operate on *clean document text*. smart-crawler's pitch is to ground against *noisy scraped HTML*, which is strictly harder and underserved. If the library nails quote verification over `fit_markdown`, that is a genuine contribution. If it punts to fuzzy match silently, it is worse than LangExtract.

## Sources

- [Google LangExtract — Developer blog](https://developers.googleblog.com/introducing-langextract-a-gemini-powered-information-extraction-library/)
- [google/langextract GitHub](https://github.com/google/langextract)
- [Anthropic Citations API announcement](https://www.anthropic.com/news/introducing-citations-api)
- [Simon Willison on Citations API](https://simonwillison.net/2025/Jan/24/anthropics-new-citations-api/)
- [Vectara HHEM leaderboard refresh](https://www.vectara.com/blog/introducing-the-next-generation-of-vectaras-hallucination-leaderboard)
- [Bohnet et al. — Attributed QA (arXiv:2212.08037)](https://arxiv.org/abs/2212.08037)
- [Attribute First, Then Generate — ACL 2024](https://aclanthology.org/2024.acl-long.182/)
- [ReClaim — arXiv:2407.01796](https://arxiv.org/abs/2407.01796)
- [LAQuer — ACL 2025](https://aclanthology.org/2025.acl-long.746.pdf)
- [RAGAS metrics](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/)
