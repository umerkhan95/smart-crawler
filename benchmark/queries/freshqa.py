"""FreshQA loader. Apache-2.0 compatible, full traces allowed in results.

Source: https://github.com/freshllms/freshqa
Data: Google Sheets export, pinned as freshqa_YYYY_MM_DD.csv in this dir.

FreshQA has 600 questions (500 TEST, 100 DEV) with:
- Multiple answer aliases (answer_0 through answer_9)
- Categories: false_premise, num_hops, fact_type
- Source URLs from the annotators

We use the TEST split by default and skip false_premise questions for the
noise benchmark (they test the LLM's refusal behavior, not retrieval
noise). This is configurable.
"""

from __future__ import annotations

import csv
from pathlib import Path

from benchmark.harness.types import BenchmarkQuery

# Pinned dataset — update by downloading a new sheet and renaming
_DATA_DIR = Path(__file__).parent
_DEFAULT_FILE = "freshqa_2025_11_24.csv"

# CSV structure: row 0 = warning, row 1 = blank, row 2 = header, row 3+ = data
_HEADER_ROW = 2
_DATA_START = 3


def load_freshqa(
    version: str | None = None,
    n: int | None = None,
    split: str = "TEST",
    include_false_premise: bool = False,
) -> list[BenchmarkQuery]:
    """Load FreshQA questions as BenchmarkQuery objects.

    Args:
        version: CSV filename (e.g. "freshqa_2025_11_24.csv"). None = latest.
        n: Max questions to return. None = all matching.
        split: "TEST" (500) or "DEV" (100). Default TEST.
        include_false_premise: If False (default), skip questions where the
            premise is false — these test refusal, not retrieval noise.
    """
    filename = version or _DEFAULT_FILE
    filepath = _DATA_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(
            f"FreshQA data not found at {filepath}. Download from "
            "https://github.com/freshllms/freshqa and save as CSV."
        )

    with open(filepath, encoding="utf-8") as f:
        rows = list(csv.reader(f))

    header = rows[_HEADER_ROW]
    data_rows = rows[_DATA_START:]

    # Build column index
    col = {name: i for i, name in enumerate(header)}

    queries: list[BenchmarkQuery] = []

    for row in data_rows:
        if len(row) <= col.get("question", 0):
            continue

        question = row[col["question"]].strip()
        if not question:
            continue

        row_split = row[col["split"]].strip()
        if row_split != split:
            continue

        is_false_premise = row[col["false_premise"]].strip().upper() == "TRUE"
        if not include_false_premise and is_false_premise:
            continue

        # Primary answer
        answer = row[col["answer_0"]].strip()
        if not answer:
            continue

        # Collect aliases (answer_1 through answer_9)
        aliases = []
        for i in range(1, 10):
            key = f"answer_{i}"
            if key in col and col[key] < len(row):
                alias = row[col[key]].strip()
                if alias:
                    aliases.append(alias)

        # Category for stratified reporting
        category_parts = []
        if "fact_type" in col:
            category_parts.append(row[col["fact_type"]].strip())
        if "num_hops" in col:
            category_parts.append(row[col["num_hops"]].strip())
        category = "|".join(filter(None, category_parts)) or None

        queries.append(
            BenchmarkQuery(
                qid=row[col["id"]].strip(),
                question=question,
                answer=answer,
                answer_aliases=aliases,
                category=category,
                source="freshqa",
                redact_in_results=False,
            )
        )

    if n is not None and n < len(queries):
        queries = queries[:n]

    return queries
