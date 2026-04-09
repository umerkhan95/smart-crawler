"""Harness-owned serialization template.

This module IS the fairness boundary. Every baseline's chunks go through
the same fixed template before the answer LLM sees them. No baseline
controls the prompt format. Changes to the template MUST bump
TEMPLATE_VERSION and be documented in benchmark/methodology.md.

Design follows field practice:
- MIRAGE: numbered chunks with document title
- LangChain: "\n\n".join(doc.page_content)
- FreshQA: structured evidence blocks with source attribution

Our template: numbered chunks with source URL attribution. Closest to
MIRAGE's approach, with the addition of source URLs (which MIRAGE omits).
"""

from __future__ import annotations

from benchmark.harness.types import BenchmarkQuery, RetrievedContext

TEMPLATE_VERSION = "v1"

ANSWER_PROMPT = """Use ONLY the retrieved context below to answer the question. If the context does not contain enough information, say "I cannot answer from the provided context."

{context}

Question: {question}

Answer:"""


def serialize_chunks(ctx: RetrievedContext) -> str:
    """Turn structured chunks into the text block for the answer LLM.

    This is the single source of truth for what the answer LLM reads.
    noise_ratio is computed over the output of this function.

    Format:
        [RETRIEVED CONTEXT]

        [1. SOURCE: https://example.com/page]
        chunk text here

        [2. SOURCE: https://example.com/other]
        chunk text here
    """
    if not ctx.chunks:
        return "[RETRIEVED CONTEXT]\n\n(no content retrieved)"

    lines = ["[RETRIEVED CONTEXT]", ""]
    for i, chunk in enumerate(ctx.chunks, 1):
        lines.append(f"[{i}. SOURCE: {chunk.source_url}]")
        lines.append(chunk.text)
        lines.append("")

    return "\n".join(lines).rstrip()


def build_answer_prompt(ctx: RetrievedContext, query: BenchmarkQuery) -> str:
    """Build the full prompt sent to the answer LLM.

    The answer LLM sees exactly this string and nothing else. Every
    baseline, every query, every run — same template. The only variables
    are the serialized chunks and the question.
    """
    context_block = serialize_chunks(ctx)
    return ANSWER_PROMPT.format(context=context_block, question=query.question)
