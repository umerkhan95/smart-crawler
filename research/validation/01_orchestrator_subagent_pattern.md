# 01 — Orchestrator + Sub-agent Pattern: State of the Field (2025-2026)

## What the field actually believes

The orchestrator + retrieval-subagent pattern is now the *dominant* published pattern for open-ended research tasks at frontier labs, but it is simultaneously the *most publicly attacked* agent pattern of 2025. Both things are true.

**Pro camp (canonical reference: Anthropic, June 2025).** Anthropic's "How we built our multi-agent research system" explicitly advocates a lead-agent + parallel sub-agent decomposition, and reports that their multi-agent Research feature outperformed a single-agent Claude baseline by ~90% on their internal research eval, driven mostly by parallel tool use. They also report the pattern burns ~15× the tokens of a chat turn, so it only makes economic sense for high-value queries ([Anthropic engineering blog](https://www.anthropic.com/engineering/multi-agent-research-system)). OpenAI Deep Research, Perplexity Deep Research, and Google's Gemini Deep Research all ship the same basic shape: a planner that fans out 20-50 searches, clusters, and synthesizes ([Perplexity Deep Research announcement](https://www.perplexity.ai/hub/blog/introducing-perplexity-deep-research), [Helicone comparison](https://www.helicone.ai/blog/openai-deep-research)). LangGraph, CrewAI, AutoGen, and MetaGPT all ship orchestrator-worker primitives as their headline abstraction.

**Contrarian camp (canonical reference: Cognition, 2025).** Cognition's "Don't Build Multi-Agents" argues the pattern is premature in 2025 because sub-agents lack the full trace of the lead agent, make conflicting implicit decisions, and the merge step is unreliable. Their two rules: *"Share context, share full agent traces"* and *"Actions carry implicit decisions; conflicting decisions carry bad results"* ([Cognition blog](https://cognition.ai/blog/dont-build-multi-agents)). Walden Yan's illustrative Flappy-Bird example — one sub-agent draws a Mario-style background, another draws a mismatched bird — is now cited as the canonical failure of naive fan-out.

**Academic camp.** Cemri et al. "Why Do Multi-Agent LLM Systems Fail?" (arXiv:2503.13657, March 2025) evaluated 7 SOTA OSS multi-agent frameworks and report **41%–86.7% task failure rates**, with failures taxonomized into specification, inter-agent misalignment, and verification errors ([arXiv](https://arxiv.org/pdf/2503.13657)). A second paper "Large Language Models Miss the Multi-Agent Mark" (arXiv:2505.21298) argues most MAS-LLM work ignores the non-determinism of LLMs and imports deterministic MAS assumptions that don't hold.

## Documented failure modes (all from Anthropic's own postmortem)

- Sub-agents duplicating each other's work on vague tasks (e.g. three sub-agents all re-researching the 2021 auto chip shortage).
- Orchestrator spawning 50 sub-agents for a trivial question ("sycophantic fan-out").
- Sub-agents stuck in loops searching for non-existent sources.
- Sub-agents interrupting each other with status updates.
- Token cost 15× a normal chat turn; economically viable only for high-value queries.
([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system), [ByteByteGo summary](https://blog.bytebytego.com/p/how-anthropic-built-a-multi-agent))

LangChain's "How and when to build multi-agent systems" (2025) reconciles the two camps: multi-agent works for *embarrassingly parallel read-only retrieval*, fails for *collaborative writing* where decisions interlock ([LangChain blog](https://blog.langchain.com/how-and-when-to-build-multi-agent-systems/)). Phil Schmid's "Single vs Multi-Agents" lands at the same conclusion ([philschmid.de](https://www.philschmid.de/single-vs-multi-agents)).

## Is the pattern oversold?

Yes and no. The *generic* "let's have 5 agents talk to each other" pattern is oversold and documented as fragile. The *specific* pattern of **one planner + N stateless read-only retrieval workers that never talk to each other and return structured artifacts** is the one Anthropic actually defends, and it's also the one that matches the Cognition "share full context" rule because there *is* no shared context to fragment — each worker returns facts, not decisions.

## Implications for smart-crawler

smart-crawler sits on the *safe* side of this debate. It is not a chatty multi-agent system. It is a single orchestrator (`pipeline.py`) dispatching deterministic workers via a fixed DAG, with exactly one or two LLM calls (planner + optional repairer). There are no agents talking to each other. The "retrieval offload" framing is aligned with Anthropic's pattern but sidesteps the Cognition critique because sub-components are not LLM agents — they are pure functions.

**Risk flag:** if smart-crawler ever grows to spawn multiple LLM planners in parallel on sub-queries (a tempting "deep research mode"), it inherits every Cognition failure mode. Keep planners serial.

## Sources

- [Anthropic — How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Cognition — Don't Build Multi-Agents](https://cognition.ai/blog/dont-build-multi-agents)
- [Cemri et al. — Why Do Multi-Agent LLM Systems Fail? (arXiv:2503.13657)](https://arxiv.org/pdf/2503.13657)
- [LangChain — How and when to build multi-agent systems](https://blog.langchain.com/how-and-when-to-build-multi-agent-systems/)
- [LLMs Miss the Multi-Agent Mark (arXiv:2505.21298)](https://arxiv.org/html/2505.21298v3)
- [Perplexity Deep Research](https://www.perplexity.ai/hub/blog/introducing-perplexity-deep-research)
- [ByteByteGo — How Anthropic Built a Multi-Agent Research System](https://blog.bytebytego.com/p/how-anthropic-built-a-multi-agent)
