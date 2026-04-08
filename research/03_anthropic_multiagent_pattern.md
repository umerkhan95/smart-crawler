# 03 — Anthropic Multi-Agent Research Pattern → smart-crawler mapping

Source: <https://www.anthropic.com/engineering/built-multi-agent-research-system>
("How we built our multi-agent research system", Anthropic Engineering, 2025).

This is the architectural reference for smart-crawler. The reasoning tier of
the caller is the **lead researcher**; smart-crawler is a **search subagent**.

## The architecture in one paragraph

A lead agent develops a plan, spawns N specialised subagents in parallel,
each subagent owns its own context window and tool budget, runs its own
search-then-think loop, and returns a *compressed* answer to the lead. The
lead synthesises across subagent outputs and either spawns more subagents or
emits the final answer. State persistence + checkpoints handle the long-tail
failure modes.

## Numbers worth memorising

- Multi-agent Claude Opus 4 outperformed single-agent Claude Opus 4 by
  **+90.2%** on internal research evals.
- Parallel tool calling cut research wall-clock by **up to 90%** on complex
  queries.
- Agents use **~4×** the tokens of chat; multi-agent systems use **~15×**.
- Token usage explains **~80%** of performance variance on browsing evals —
  so spending tokens is the lever, but the value of the task has to justify
  the bill.
- A single prompt-engineering improvement to tool descriptions cut task
  completion time **40%**.
- A 20-query eval set was enough to take success from **30% → 80%** during
  early iteration.

## Lessons that change smart-crawler's design

### 1. The subagent must own its context window
Each subagent has a private scratchpad. The lead never sees raw search
results — only the subagent's compressed answer. **Implication:** the
`smart_search` return value must be a *compressed, schema-valid, cited*
payload. Raw markdown / raw HTML must never leak back to the caller. This is
already in our CLAUDE.md ("LLM is a planner, not a reader") but Anthropic's
data is the empirical justification.

### 2. Delegation needs explicit task specs
"Without detailed task descriptions, agents duplicate work, leave gaps, or
fail to find necessary information." **Implication:** smart-crawler's
contract must accept *structured* delegation, not just a free-text query.
This is exactly what `Query(query, mode, schema_hint, freshness, budget,
must_cite)` is — keep it strict.

### 3. Effort must scale with query difficulty
Anthropic embeds explicit rules in prompts: "simple fact-finding = 1 agent,
3–10 tool calls; complex research = 10+ subagents". **Implication:** our
`router.py` should classify (cheap snippet | single-page extract | deep
crawl | adaptive crawl) and pick a different pipeline branch with *very*
different budgets. The router is non-optional, even in v1.

### 4. Search should go broad → narrow
Subagents "start with short, broad queries, evaluate what's available, then
progressively narrow focus." **Implication:** `probe.py` runs a cheap
broad pass first (URL discovery via `prefetch=True`, or DuckDuckGo /
serp-style snippet fetch) before committing to a deep crawl on a specific
domain.

### 5. Parallel subagents > sequential
The 90% wall-clock win came from spawning subagents simultaneously.
**Implication:** when the caller requests N entities ("CEO of these 20
startups"), smart-crawler must dispatch N parallel sub-pipelines through
`MemoryAdaptiveDispatcher`, not loop. Each sub-pipeline carries its own
budget envelope.

### 6. Tool descriptions are make-or-break
40% time savings from better tool docs. **Implication:** the docstring of
`smart_search` is *part of the product*. It will end up in the calling
agent's tool catalog and drive its behaviour. We should write it as if it's
the only documentation that exists.

### 7. Stateful errors compound; deterministic safeguards win
Anthropic combines AI adaptability with retry logic + checkpoints.
**Implication:** every step in `pipeline.py` writes a checkpoint (the same
state file `AdaptiveCrawler.save_state` produces is fine), and the LLM is
*never* asked to retry — the orchestrator code is.

### 8. LLM-as-judge eval, started small
20 representative queries, single LLM judge call rubric (factual accuracy,
citation precision, completeness, source quality, tool efficiency).
**Implication:** `tests/integration/` should ship with a 20-query
golden-set fixture and an `eval_judge.py` harness from day one, not as a
Phase 5 nice-to-have.

### 9. Synchronous bottleneck is real
Even Anthropic admits "lead agents wait for each set of subagents to
complete before proceeding." Our `smart_search` is sync-by-design (it
returns when done), but inside, every fan-out should be `asyncio.gather`,
never a for-loop.

### 10. The prototype-to-production gap is wider than expected
Specifically because of compound errors. **Implication:** the
"summary mode with mandatory citations" (Phase 3 in plans.md) is the *test
of the architecture*, not a feature. If summary mode silently drops
citations under load, the architecture is wrong.

## What does NOT map

- Anthropic uses long-running multi-turn conversations between lead and
  subagent. We don't — `smart_search` is one shot. The closest analogue is
  the `repairer.py` loop, which is bounded (max 1–2 retries).
- Anthropic's "rainbow deployments" only matter if smart-crawler is a
  long-lived service. For v1 it's a library.
- Their "external memory" pattern (store research plans on disk to survive
  context limits) is overkill until we hit the AdaptiveCrawler 200-page case.
