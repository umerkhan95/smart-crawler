# smart-crawler build plan

Stateless, open-source. No persistence layer at any phase.

## Phase 0 — Scaffolding (done)
- [x] Repo init, README, CLAUDE.md, plans.md
- [x] Package skeleton
- [x] `pyproject.toml` (uv, dev deps, ruff/basedpyright/pytest config)
- [x] `.pre-commit-config.yaml` (ruff, basedpyright, bandit, semgrep)
- [x] Public API stub: `smart_search()` signature
- [x] License (Apache-2.0)

## Phase 1 — Research (done, see `research/`)
- [x] crawl4ai 0.8.x API surface
- [x] Adaptive stopping (info-gain vs schema-completeness)
- [x] Anthropic orchestrator + subagent pattern
- [x] Citation grounding (crawl4ai has none — citer is the keystone)
- [x] Schema inference (`generate_schema()` is the second LLM call)
- [x] Design synthesis with concrete signatures

## Phase 2 — Core modules (SRP, no cross-imports)
- [ ] `types.py`        — Query, Source, Fact, Result, Budget, ExtractionPlan
- [ ] `router.py`       — snippet / single-page / deep / adaptive (4 branches, day one)
- [ ] `planner.py`      — LLM: query + sample pages → ExtractionPlan
                          (uses crawl4ai's `generate_schema` under the hood)
- [ ] `probe.py`        — run plan on 1 page, return coverage score
- [ ] `crawler.py`      — BestFirst + AdaptiveCrawler wrapper, polite defaults
- [ ] `extractor.py`    — deterministic CSS/XPath extraction
- [ ] `repairer.py`     — LLM fallback for failed pages, tags as `llm_fallback`
- [ ] `citer.py`        — KEYSTONE. Attaches {url, quote, retrieved_at} to
                          every fact. Drops anything ungrounded.
- [ ] `pipeline.py`     — composes everything; owns the structured-mode stop
                          loop (schema-completeness, not crawl4ai's saturation)

## Phase 3 — Public API + eval
- [ ] `smart_search(query, mode, schema, budget, must_cite)` end-to-end
- [ ] `structured` mode on one real site
- [ ] `summary` mode with mandatory citations (uses AdaptiveCrawler stop)
- [ ] `tests/integration/golden_set.json` — 20 representative queries
- [ ] Eval harness: pass-rate against golden set (Anthropic's 30→80% lever)

## Phase 4 — Hardening
- [ ] Graceful failure surface (`retrieval_error` with reason)
- [ ] Re-plan trigger when intra-call repair rate exceeds threshold
- [ ] Concurrent dispatch via `MemoryAdaptiveDispatcher`
- [ ] Property-based fuzzing of extractors (hypothesis)
- [ ] `robots.txt` respect verified, User-Agent set

## Notes
- **Citer is the keystone**, not a thin module. crawl4ai's
  `LLMExtractionStrategy` returns no quote spans / offsets. We own provenance.
- **Don't use `AdaptiveCrawler` for structured mode** — its saturation metric
  quits early on sparse-fact queries. Drive the loop in `pipeline.py` using
  schema-completeness as the stop signal. Reserve `AdaptiveCrawler` for
  `summary` mode.
- **Router is v1**, not Phase 4. Snippet vs deep is the difference between
  "fast cheap answer" and "burns the budget on every query."
- **Eval harness ships with Phase 3**, not Phase 5. 20 golden queries cost
  almost nothing and gate every change.
