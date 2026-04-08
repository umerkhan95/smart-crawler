# 04 — Citation Grounding (forcing extractions to carry verifiable provenance)

Sources:
- <https://www.tensorlake.ai/blog/rag-citations> — fine-grained citation patterns
- <https://arxiv.org/html/2512.12117v1> — *Citation-Grounded Code Comprehension*
  (mechanical citation verification via interval arithmetic over line ranges)
- <https://arxiv.org/html/2311.09533v3> — *Effective LLM Adaptation for
  Improved Grounding and Citation Generation*
- <https://www.elastic.co/search-labs/blog/grounding-rag>
- <https://www.deepset.ai/blog/rag-llm-evaluation-groundedness>
- crawl4ai source: `crawl4ai/extraction_strategy.py` (verified — no built-in
  grounding, see [`01_crawl4ai_api_surface.md`](01_crawl4ai_api_surface.md) §4)

This is the most architecturally consequential research file. **Crawl4ai
gives us nothing here.** Smart-crawler must own grounding end to end.

## The core problem

LLM extraction returns `{"ceo": "Jane Doe"}`. The string "Jane Doe" has no
audit trail back to the source HTML. Three failure modes follow:

1. **Hallucination** — Jane Doe was never on the page.
2. **Misattribution** — Jane Doe is on the page but is the COO, not CEO.
3. **Stale provenance** — Jane Doe was on the page yesterday but the page
   changed; we can't tell because we never recorded the snippet.

Production RAG systems converge on the same fix: every emitted fact carries
a `(source_id, char_offset_start, char_offset_end, verbatim_quote)` tuple,
and the system *mechanically* verifies the quote exists in the source before
returning. The LLM is never trusted to self-cite.

## Production patterns (in order of robustness)

### A. Quote-span extraction (offset tracking)
Ask the LLM to return both the value and a verbatim span:
```json
{"ceo": {"value": "Jane Doe",
         "quote": "Our CEO Jane Doe joined in 2019",
         "char_start": 1842, "char_end": 1873}}
```
Then code (not LLM) verifies `source[char_start:char_end] == quote`. If not,
locate `quote` in source via exact substring search; if still not found,
*the fact is rejected*. Tensorlake calls this "spatial anchoring."
This is what we want for both `structured` and `summary` modes.

### B. Mechanical interval verification
arXiv 2512.12117 generalises (A): the LLM cites `[file:start-end]`, and an
interval-arithmetic check enforces that the citation interval *intersects*
a chunk that was actually retrieved. The model literally "cannot cite code
it hasn't seen." The same trick works for HTML: assign every chunk an
`(url, idx, char_start, char_end)` tuple at retrieval time, force the LLM
to cite a chunk id, and reject any answer whose chunk id wasn't in its
context. This is the right model for `repairer.py` LLM fallback.

### C. Verification loops
After extraction, re-prompt a *cheaper* model: "Does the snippet S support
the claim C? yes/no." Reject `no`s. The deepset blog calls this
"groundedness scoring." Use sparingly — it doubles LLM calls and CLAUDE.md
budgets us to <5 per domain.

### D. Per-claim provenance, no aggregate citations
arXiv 2311.09533 shows aggregate "Sources: [1][2][3]" at the end of an
answer is meaningless — readers (and downstream agents) can't tell which
claim came from which source. Every individual fact must point at *its
own* source. This matches our `Fact.sources: list[Source]` model. Keep it.

## What crawl4ai's `LLMExtractionStrategy` does NOT do

Verified against `crawl4ai/extraction_strategy.py`:
- No `quote` field in extracted JSON
- No char-offset tracking
- No retrieval-context interval check
- `self.usages` only tracks token *cost*, not provenance
- `force_json_response=True` enforces shape, not grounding

**Implication:** smart-crawler cannot delegate grounding to crawl4ai. It
must wrap `LLMExtractionStrategy` in a `citer.py` that does (A) + (B) on
the way out. The deterministic `JsonCssExtractionStrategy` path is easier:
the selector *is* the provenance — record the matched text and the CSS path
that produced it.

## Concrete grounding contract for smart-crawler

For every `Fact` returned:

1. **Deterministic path** (`extracted_by="deterministic"`):
   - `Source.url` = page URL
   - `Source.quote` = the matched-element `.text_content()` exactly as the
     selector found it (no LLM normalisation)
   - `Source.retrieved_at` = `result.metadata.fetched_at`
   - We do not need char offsets — the CSS selector itself can be stored
     in a debug field if needed.
2. **LLM-fallback path** (`extracted_by="llm_fallback"`):
   - Force the prompt to return `{value, quote}` per field.
   - Verify `quote in fit_markdown` (case-insensitive, whitespace-normalised).
   - On miss: try fuzzy search (rapidfuzz `partial_ratio >= 92`); on
     second miss, *drop the fact and increment `errors`*.
   - Set `confidence = fuzzy_ratio / 100`.

3. **Summary mode**:
   - The summary is a list of `(sentence, [Source, ...])` pairs, not a
     single blob. Sentences without at least one verified source are
     dropped. This is the only way to honour `must_cite=True`.

## Edge cases to plan for

- **Translations / paraphrase**: the LLM rewrites "CEO since 2019" to
  "Chief Executive". Substring check fails. Fix: pre-normalise (lowercase,
  collapse whitespace) before comparison; allow ≤8% character distance.
- **PDF / image content**: char offsets meaningless; fall back to page
  number + bounding box from crawl4ai's PDF extractor.
- **JavaScript-rendered content**: `wait_for` must complete before we
  snapshot the markdown that becomes our provenance baseline. Otherwise the
  quote may exist in the visible page but not in our recorded source.
- **Multiple matches**: if `quote` appears 3 times in the page, that's fine
  — record the first hit's offset. We are verifying *existence*, not
  *uniqueness*.

## TL;DR for implementation

`citer.py` is not optional and is not small. It's the module that turns
smart-crawler from "another crawl4ai wrapper" into "a retrieval API you can
trust." Budget real time for it, and write the verification tests *first*.
