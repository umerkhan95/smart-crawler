"""Public API. The only function external callers should use."""

from __future__ import annotations

from typing import Any

from smart_crawler.types import Budget, Mode, Query, Result


def smart_search(
    query: str,
    mode: Mode = "structured",
    schema: dict[str, Any] | None = None,
    freshness: str | None = None,
    budget: Budget | None = None,
    must_cite: bool = True,
) -> Result:
    """Offloaded web retrieval.

    Returns schema-valid, cited facts. Raises NotImplementedError until the
    pipeline is wired up (Phase 3).
    """
    q = Query(
        query=query,
        mode=mode,
        schema_hint=schema,
        freshness=freshness,
        budget=budget or Budget(),
        must_cite=must_cite,
    )
    raise NotImplementedError(
        "smart_search pipeline not yet implemented; see plans.md Phase 3."
    )
