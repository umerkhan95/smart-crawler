"""FreshQA loader. Apache-2.0, full traces allowed in results.

Source: https://github.com/freshllms/freshqa
"""

from __future__ import annotations

from benchmark.harness.types import BenchmarkQuery


def load_freshqa(version: str | None = None, n: int | None = None) -> list[BenchmarkQuery]:
    """Load FreshQA queries. version=None means latest snapshot at run time."""
    raise NotImplementedError("freshqa.load_freshqa — Phase 2 stub")
