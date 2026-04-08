# 06 — Stateless vs Stateful Retrieval Agents (2025-2026)

## Current landscape

- **LangChain / LangGraph**: explicitly *stateful*. LangGraph's headline differentiator in 2025 is checkpointing, durable execution, pause/resume, human-in-the-loop. Pitch: state is a feature, not a bug ([LangChain vs LlamaIndex comparison](https://www.morphllm.com/comparisons/langchain-vs-llamaindex)).
- **LlamaIndex Workflows**: *stateless by default*. Users have to bolt on their own persistence if they want it. Benchmarked ~6ms framework overhead vs LangChain ~10ms / LangGraph ~14ms ([ZenML comparison](https://www.zenml.io/blog/llmindex-vs-langchain), [Latenode 2025 comparison](https://latenode.com/blog/platform-comparisons-alternatives/automation-platform-comparisons/langchain-vs-llamaindex-2025-complete-rag-framework-comparison)).
- **Haystack**: stateful pipelines with component-level state, but the retrieval layer can be used stateless.
- **CrewAI / AutoGen**: stateful by default — memory is a first-class concept.
- **Crawl4AI**: stateless at the library level (no DB), but caches browser contexts and can be configured with a cache layer.
- **Firecrawl**: stateless API calls; state lives on the server.
- **GPT Researcher**: stateless per research task; state lives only for the duration of a run.

**So the answer to "does anyone ship a fully stateless retrieval layer?" is: LlamaIndex (workflows), Crawl4AI (library), Firecrawl (API), and GPT Researcher (per-run).** It is not an unusual design — it is one of two standard options.

## What production teams report

The 2025 consensus is the "hybrid":
> "Most production RAG systems in 2026 use both: LlamaIndex for the data and retrieval layer, LangGraph for orchestration and agent logic."
([Morph comparison](https://www.morphllm.com/comparisons/langchain-vs-llamaindex))

Stateful retrieval layers are used when:
- Multi-turn conversational agents need to remember what they already fetched.
- The cost of re-fetching is high (paid APIs, long crawls).
- Deduplication across sessions matters.
- Learning-over-time (adaptive site plans, selector self-healing) is a feature.

Stateless retrieval layers win when:
- Reproducibility and auditability matter (every call is a pure function of inputs).
- The deploy target is serverless / ephemeral / edge.
- The library is meant to drop into someone else's agent stack without imposing a storage backend.
- "No infra" is a feature (e.g. an OSS library users just `pip install`).

## Is "no cache, no DB" a feature or a foot-gun in 2026?

**Both, depending on audience.** Enterprise teams with long-running research agents will find stateless painful — they will re-fetch the same pages repeatedly and re-run the same LLM planner calls, which at scale is expensive. The Redis blog makes this case for stateful explicitly ([Redis AI memory](https://redis.io/blog/ai-agent-memory-stateful-systems/)).

For a **library meant to be imported into other people's agents**, stateless is the right default because:
1. The caller already has their own state/cache/DB stack.
2. Imposing a cache backend breaks the "one-liner install" promise.
3. Idempotent pure-function semantics compose cleanly with any orchestration layer (LangGraph, Temporal, Prefect).
4. It is the design LlamaIndex Workflows defaults to, and they are the closest analog.

The foot-gun risk is not statelessness per se — it is **statelessness without a clean cache-as-middleware extension point**. LlamaIndex solved this by letting users wrap workflows with their own persistence. If smart-crawler forbids cache entirely with no extension point, power users will fork it to add one, which is worse than exposing a `cache_backend=None` parameter from day one.

## The Cognition angle

Cognition's "don't build multi-agents" critique is about *decision fragmentation*, not statefulness. A stateless retrieval *library* used by a stateful *agent* does not trigger any of Cognition's failure modes, because the library is a pure function. So stateless in smart-crawler's position is orthogonal to the multi-agent debate.

## Implications for smart-crawler

smart-crawler's stateless stance is **aligned with one of two mainstream approaches** — specifically the LlamaIndex/Crawl4AI/Firecrawl side. It is not novel and it is not off-trend. The "pip install and go" framing is a legitimate product differentiator against LangGraph-centric stacks.

**Risk flag:** the CLAUDE.md rule "no cache, no DB, no on-disk artifacts" is stricter than necessary. LlamaIndex and Crawl4AI are "stateless by default" but allow users to opt in to caching. smart-crawler forbidding it entirely means:
1. Every re-run re-fetches every page — a benchmark-repeatability footgun on the golden set itself.
2. No way to amortize planner cost across calls for the same domain.
3. Power users will fork to add caching.

**Recommendation:** reframe the rule from "no cache ever" to "**no implicit state; caller-provided cache only**." Same architectural purity, no foot-gun. A `cache: CacheBackend | None = None` parameter is an order of magnitude friendlier than a hard ban.

**Novelty flag:** none. Stateless retrieval is well-trodden ground.

## Sources

- [Morph — LangChain vs LlamaIndex 2026](https://www.morphllm.com/comparisons/langchain-vs-llamaindex)
- [ZenML — LlamaIndex vs LangChain](https://www.zenml.io/blog/llmindex-vs-langchain)
- [Latenode — LangChain vs LlamaIndex 2025](https://latenode.com/blog/platform-comparisons-alternatives/automation-platform-comparisons/langchain-vs-llamaindex-2025-complete-rag-framework-comparison)
- [Redis — AI agent memory and stateful systems](https://redis.io/blog/ai-agent-memory-stateful-systems/)
- [State Management for AI Agents — ByAITeam Dec 2025](https://byaiteam.com/blog/2025/12/14/state-management-for-ai-agents-stateless-vs-persistent/)
