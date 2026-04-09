"""Full pilot: B0 + B5a/b/c/d + B6 on 10 FreshQA questions.

Tests every Tavily mode per the docs, plus the naive floor and
the LLM search (snippet) baseline.

Usage: python -m benchmark.pilot_full
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from benchmark.baselines.b0_naive import NaiveBaseline
from benchmark.baselines.b5_tavily import (
    TavilyAdvancedChunksBaseline,
    TavilyAnswerBaseline,
    TavilyRawBaseline,
    TavilySearchExtractBaseline,
)
from benchmark.harness import metrics, serializer
from benchmark.harness.judge import judge_equivalence
from benchmark.harness.llm import complete
from benchmark.harness.tokenizer import count_tokens, get_encoding_name
from benchmark.harness.types import BenchmarkQuery, RetrievedChunk, RetrievedContext
from benchmark.queries.freshqa import load_freshqa
from tavily import AsyncTavilyClient

N_QUESTIONS = 10
ANSWER_MODEL = "gpt-4o-mini"
JUDGE_MODEL = "gpt-4o-mini"


async def evaluate_one(name: str, baseline, query: BenchmarkQuery) -> dict:
    print(f"  [{name}] Retrieving...")
    try:
        ctx = await baseline.retrieve(query)
    except Exception as e:
        print(f"  [{name}] FAILED: {e}")
        return {"qid": query.qid, "baseline": name, "error": str(e)}

    serialized = serializer.serialize_chunks(ctx)
    context_tokens = count_tokens(serialized, model=ANSWER_MODEL)
    noise, _, span_tokens = metrics.compute_noise_ratio(ctx, query, model=ANSWER_MODEL)

    if metrics.exact_match_accuracy(ctx, query):
        accuracy, judge_used = 1, False
    else:
        prompt = serializer.build_answer_prompt(ctx, query)
        candidate = await complete(prompt=prompt, model=ANSWER_MODEL, temperature=0.0, max_tokens=256)
        is_eq = await judge_equivalence(query.question, query.answer, candidate, model=JUDGE_MODEL)
        accuracy, judge_used = (1 if is_eq else 0), True

    status = "✅" if accuracy else "❌"
    noise_s = f"{noise:.2%}" if noise is not None else "N/A"
    print(f"  [{name}] {status} tokens={context_tokens:,} noise={noise_s} chunks={len(ctx.chunks)}")

    return {
        "qid": query.qid, "baseline": name,
        "question": query.question[:80], "ground_truth": query.answer[:80],
        "chunks_returned": len(ctx.chunks), "context_tokens": context_tokens,
        "answer_span_tokens": span_tokens,
        "noise_ratio": round(noise, 6) if noise is not None else None,
        "accuracy": accuracy, "judge_used": judge_used,
        "bytes_fetched": ctx.bytes_fetched,
    }


async def run_b6_snippet(query: BenchmarkQuery) -> RetrievedContext:
    """B6: Tavily snippets only — simulates LLM WebSearch."""
    client = AsyncTavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    resp = await client.search(
        query=query.question, max_results=5,
        include_raw_content=False, include_answer=False,
    )
    chunks = []
    total_bytes = 0
    for r in resp.get("results", []):
        text = r.get("content", "")
        if text:
            total_bytes += len(text.encode("utf-8"))
            chunks.append(RetrievedChunk(text=text, source_url=r.get("url", "")))
    return RetrievedContext(chunks=chunks, fetched_at=datetime.now(timezone.utc), bytes_fetched=total_bytes)


class B6Wrapper:
    id = "b6_llm_search"
    name = "LLM search (snippets only)"
    async def retrieve(self, query, shared_urls=None):
        return await run_b6_snippet(query)


async def main():
    print("=" * 80)
    print("FULL PILOT — All Tavily modes + B0 + B6 — 10 FreshQA questions")
    print(f"Date: {datetime.now(timezone.utc).isoformat()}")
    print(f"Model: {ANSWER_MODEL} | Tokenizer: {get_encoding_name(ANSWER_MODEL)}")
    print("=" * 80)

    queries = load_freshqa(n=N_QUESTIONS)
    print(f"Loaded {len(queries)} questions\n")

    baselines = [
        ("B0_naive", NaiveBaseline()),
        ("B5a_raw", TavilyRawBaseline()),
        ("B5b_answer", TavilyAnswerBaseline()),
        ("B5c_search_extract", TavilySearchExtractBaseline()),
        ("B5d_advanced_chunks", TavilyAdvancedChunksBaseline()),
        ("B6_llm_search", B6Wrapper()),
    ]

    all_results = []

    for i, query in enumerate(queries):
        print(f"\n{'='*60}")
        print(f"Q{i+1}/{len(queries)}: {query.question[:65]}")
        print(f"Answer: {query.answer[:65]}")
        print(f"{'='*60}")

        for name, bl in baselines:
            r = await evaluate_one(name, bl, query)
            all_results.append(r)

    # Summary table
    print("\n" + "=" * 100)
    print("SUMMARY TABLE")
    print("=" * 100)
    print(f"{'Baseline':<25} {'Acc':>5} {'Noise':>8} {'Avg Tokens':>12} {'Total Tokens':>14} {'Avg Bytes':>12}")
    print("-" * 100)

    for name, _ in baselines:
        rs = [r for r in all_results if r.get("baseline") == name and "error" not in r]
        if not rs:
            print(f"{name:<25} {'FAIL':>5}")
            continue
        noise_vals = [r["noise_ratio"] for r in rs if r["noise_ratio"] is not None]
        acc_vals = [r["accuracy"] for r in rs]
        token_vals = [r["context_tokens"] for r in rs]
        bytes_vals = [r["bytes_fetched"] for r in rs]

        avg_noise = sum(noise_vals) / len(noise_vals) if noise_vals else 0
        avg_acc = sum(acc_vals) / len(acc_vals)
        avg_tokens = sum(token_vals) / len(token_vals)
        total_tokens = sum(token_vals)
        avg_bytes = sum(bytes_vals) / len(bytes_vals)

        print(f"{name:<25} {avg_acc:>4.0%} {avg_noise:>7.2%} {avg_tokens:>12,.0f} {total_tokens:>14,} {avg_bytes:>12,.0f}")

    # Save
    out_path = Path("benchmark/results/pilot_full.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
