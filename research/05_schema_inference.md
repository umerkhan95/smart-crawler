# 05 — Schema Inference (when the caller passes only a query)

Sources:
- crawl4ai source `crawl4ai/extraction_strategy.py`
  → `JsonElementExtractionStrategy.generate_schema(html, schema_type, query, target_json_example)`
- <https://python.useinstructor.com/concepts/models/> — Instructor library
- <https://pydantic.dev/articles/llm-intro> — Pydantic + LLM patterns
- <https://docs.pydantic.dev/latest/concepts/models/#dynamic-model-creation>
  — `pydantic.create_model` for runtime model construction
- <https://realpython.com/pydantic-ai/> — Pydantic AI structured outputs

The `smart_search(schema=None, ...)` path needs a Pydantic schema *fast,
once, cheap*. Three families of approaches.

## Approach 1 — LLM-generated Pydantic schema (recommended for v1)

Single LLM call: input is the query + 1–3 short page samples; output is a
Pydantic-shaped JSON schema we feed into `pydantic.create_model`.

```python
from pydantic import create_model, Field

# LLM returns:
# {"name": "Company", "fields": {
#    "name": {"type": "str", "description": "Legal company name", "required": True},
#    "ceo": {"type": "str", "required": False},
#    "hq_city": {"type": "str", "required": False},
# }}

TYPE_MAP = {"str": str, "int": int, "float": float, "bool": bool,
            "list[str]": list[str], "datetime": "datetime"}

def build_model(spec: dict) -> type:
    fields = {}
    for fname, fdef in spec["fields"].items():
        py_type = TYPE_MAP[fdef["type"]]
        default = ... if fdef.get("required") else None
        fields[fname] = (py_type, Field(default, description=fdef.get("description")))
    return create_model(spec["name"], **fields)
```

**Pros:** flexible, one LLM call (within our <5 budget), no library deps.
**Cons:** schema quality depends on prompt; need to whitelist allowed types
to keep `eval`-style injection out; need to cache by `(query, domain)` so
we never re-infer for the same job.

## Approach 2 — `JsonElementExtractionStrategy.generate_schema` (crawl4ai built-in)

Crawl4ai already ships an LLM-driven schema generator that builds **CSS or
XPath selectors**, not Pydantic models. Signature (verified from source):

```python
JsonElementExtractionStrategy.generate_schema(
    html: str,
    schema_type: str = "CSS",        # or "XPATH"
    query: str | None = None,
    target_json_example: dict | None = None,
    llm_config: LLMConfig | None = None,
)  # -> dict, the same baseSelector/fields schema JsonCssExtractionStrategy consumes
```

It runs a **3-round refinement loop** internally: generate → test on the
HTML → refine on errors. This is *exactly* what `planner.py` should call.

**Critical insight:** approach 1 and approach 2 are *complementary*, not
competing.
- Approach 1 gives us the **caller-facing Pydantic model** (what the
  reasoning agent gets back).
- Approach 2 gives us the **deterministic CSS schema** (how we extract
  from each page without LLM calls).

The natural flow:

```
query + sample_html
   ├─► LLM call 1: generate_pydantic_spec(query, sample_html)  →  Company model
   └─► LLM call 2: generate_schema(html, "CSS",
                       target_json_example=Company().model_dump()) → css_schema
```

Two LLM calls, one per domain, both cached. Inside the budget.

## Approach 3 — Example-based induction / template library

Maintain a library of pre-built schemas keyed by domain pattern
(`shopify.com/*/products/*`, `*/about*`, `*/team*`). When a query arrives,
match the seed URL against the library; if hit, skip LLM entirely.

**Pros:** zero LLM calls for known patterns; this is the
merchant_onboarding playbook.
**Cons:** doesn't help cold-start for arbitrary sites; library maintenance
burden. Worth doing as a *cache layer in front of* approaches 1+2, not
instead of them.

## Approach 4 — Pure example-based (no LLM)

Given 2+ pages, infer fields by structural diff: elements that appear in
the same DOM position but with different text are "field candidates."
Tools like `autoextract`, the old `scrapely` library, and Diffbot do this.

**Pros:** zero LLM cost.
**Cons:** brittle; field naming becomes a separate problem ("text_3" is
not a field name); deprecated by everyone in favour of LLM approaches.
Skip for v1.

## Tradeoffs at a glance

| Approach | LLM calls | Cold-start? | Multi-domain? | Quality |
|---|---|---|---|---|
| 1. LLM Pydantic | 1 | ✓ | ✓ | High |
| 2. crawl4ai `generate_schema` | 1 (+refine) | ✓ | ✓ | High (selector-grade) |
| 3. Template library | 0 | ✗ | ✓ if known | Highest where it hits |
| 4. Pure example diff | 0 | ✓ | ✓ | Low |

## Recommendation

**Hybrid 3 → 1 → 2:**

```
planner.py:
    if domain in template_library:           # approach 3
        return library[domain]
    sample = probe.fetch_one(seed_url)       # 1 page only
    pydantic_model = llm_infer_pydantic(query, sample)        # approach 1
    css_schema   = generate_schema(sample.html, "CSS",
                                   target_json_example=...)   # approach 2
    return ExtractionPlan(pydantic_model, css_schema)
```

This costs at most **2 LLM calls per new domain**, both cached on
`(domain, query_fingerprint)`. CLAUDE.md's "<5 LLM calls per domain for
bulk jobs" budget holds with room to spare for `repairer.py`.

## Implementation gotchas

- **`create_model` and forward refs**: nested models need to be built
  bottom-up. Topo-sort the spec before instantiation.
- **Type whitelist**: never `eval()` LLM type strings. Hard-coded
  `TYPE_MAP` only.
- **Optional vs required**: default to *optional* — over-strict required
  fields mean a single missing field on one page kills the whole record.
  Validate completeness at the *result level* in `pipeline.py`, not at the
  schema level.
- **Cache key**: `sha256(query_normalised + domain)` is enough. Don't
  cache on URL — too granular.
- **Schema drift**: re-run inference if `repairer.py` failure rate exceeds
  20% on a domain — the site changed.
