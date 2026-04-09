"""First pilot run: B0 (naive) vs B5 (Tavily) on 10 FreshQA questions.

This script runs outside the full runner harness to keep things simple
and debuggable for the first ever benchmark execution. Once this works,
we'll run through runner.run() properly.

Usage: python -m benchmark.pilot
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from benchmark.baselines.b0_naive import NaiveBaseline
from benchmark.baselines.b5_tavily import TavilyBaseline
from benchmark.harness import metrics, serializer
from benchmark.harness.judge import judge_equivalence
from benchmark.harness.search import search_urls
from benchmark.harness.tokenizer import count_tokens, get_encoding_name
from benchmark.harness.types import BenchmarkQuery, RetrievedContext
from benchmark.queries.freshqa import load_freshqa

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

N_QUESTIONS = 10
ANSWER_MODEL = "gpt-4o-mini"
JUDGE_MODEL = "gpt-4o-mini"
MODE = "e2e"  # baselines discover their own URLs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def call_answer_llm(prompt: str, model: str) -> str:
    from benchmark.harness.llm import complete
    return await complete(prompt=prompt, model=model, temperature=0.0, max_tokens=256)


async def evaluate_one(
    baseline_name: str,
    baseline,
    query: BenchmarkQuery,
) -> dict:
    """Run one baseline on one query, return a summary dict."""
    print(f"  [{baseline_name}] Retrieving for: {query.question[:60]}...")

    try:
        ctx: RetrievedContext = await baseline.retrieve(query)
    except Exception as e:
        print(f"  [{baseline_name}] RETRIEVAL FAILED: {e}")
        return {
            "qid": query.qid,
            "baseline": baseline_name,
            "error": str(e),
        }

    # Serialize and count tokens
    serialized = serializer.serialize_chunks(ctx)
    context_tokens = count_tokens(serialized, model=ANSWER_MODEL)
    chunks_returned = len(ctx.chunks)

    # Noise ratio
    noise, _, span_tokens = metrics.compute_noise_ratio(ctx, query, model=ANSWER_MODEL)

    # Accuracy: exact match first
    if metrics.exact_match_accuracy(ctx, query):
        accuracy = 1
        judge_used = False
        candidate = "(exact match — no LLM call needed)"
    else:
        # Call answer LLM
        prompt = serializer.build_answer_prompt(ctx, query)
        candidate = await call_answer_llm(prompt, ANSWER_MODEL)

        # Judge
        is_equiv = await judge_equivalence(
            question=query.question,
            ground_truth=query.answer,
            candidate=candidate,
            model=JUDGE_MODEL,
        )
        accuracy = 1 if is_equiv else 0
        judge_used = True

    result = {
        "qid": query.qid,
        "baseline": baseline_name,
        "question": query.question[:80],
        "ground_truth": query.answer[:80],
        "candidate": candidate[:80] if candidate else "",
        "chunks_returned": chunks_returned,
        "context_tokens": context_tokens,
        "answer_span_tokens": span_tokens,
        "noise_ratio": round(noise, 4) if noise is not None else None,
        "accuracy": accuracy,
        "judge_used": judge_used,
        "bytes_fetched": ctx.bytes_fetched,
    }

    status = "✅" if accuracy else "❌"
    noise_str = f"{noise:.1%}" if noise is not None else "N/A"
    print(f"  [{baseline_name}] {status} acc={accuracy} noise={noise_str} tokens={context_tokens} chunks={chunks_returned}")

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main():
    print("=" * 70)
    print("SMART-CRAWLER BENCHMARK — FIRST PILOT RUN")
    print(f"Date: {datetime.now(timezone.utc).isoformat()}")
    print(f"Questions: {N_QUESTIONS} (FreshQA TEST, no false premise)")
    print(f"Baselines: B0 (naive) vs B5 (Tavily)")
    print(f"Mode: {MODE}")
    print(f"Answer model: {ANSWER_MODEL}")
    print(f"Judge model: {JUDGE_MODEL}")
    print(f"Tokenizer: {get_encoding_name(ANSWER_MODEL)}")
    print("=" * 70)

    # Load questions
    queries = load_freshqa(n=N_QUESTIONS)
    print(f"\nLoaded {len(queries)} questions\n")

    # Init baselines
    b0 = NaiveBaseline()
    b5 = TavilyBaseline()

    all_results = []

    for i, query in enumerate(queries):
        print(f"\n--- Question {i+1}/{len(queries)}: {query.question[:70]} ---")
        print(f"    Ground truth: {query.answer[:70]}")

        r0 = await evaluate_one("B0_naive", b0, query)
        r5 = await evaluate_one("B5_tavily", b5, query)
        all_results.extend([r0, r5])

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for baseline_name in ["B0_naive", "B5_tavily"]:
        results = [r for r in all_results if r.get("baseline") == baseline_name and "error" not in r]
        if not results:
            print(f"\n{baseline_name}: all queries failed")
            continue

        noise_values = [r["noise_ratio"] for r in results if r["noise_ratio"] is not None]
        acc_values = [r["accuracy"] for r in results]
        token_values = [r["context_tokens"] for r in results]

        avg_noise = sum(noise_values) / len(noise_values) if noise_values else 0
        avg_acc = sum(acc_values) / len(acc_values) if acc_values else 0
        avg_tokens = sum(token_values) / len(token_values) if token_values else 0

        print(f"\n{baseline_name}:")
        print(f"  Noise ratio:     {avg_noise:.1%} (avg over {len(noise_values)} queries)")
        print(f"  Accuracy:        {avg_acc:.1%} ({sum(acc_values)}/{len(acc_values)})")
        print(f"  Avg tokens:      {avg_tokens:.0f}")

    # Save raw results
    out_path = Path("benchmark/results/pilot_run.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nRaw results saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
