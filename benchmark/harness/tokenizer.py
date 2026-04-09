"""Token counting — the single source of truth.

Every token count in the benchmark flows through this module. No other
module is allowed to call tiktoken directly. This isolation means we can
swap tokenizers (e.g., for Claude via Anthropic API) without touching
metrics, runner, or any baseline.

Design decisions (backed by 2025-2026 field research):

1. Use encoding_for_model() as primary, o200k_base as fallback.
   - cl100k_base is deprecated (still works but not recommended for new
     work). RAGAS already moved to o200k_base.
   - encoding_for_model() auto-maps model names to the right encoding.
   - Unknown models (Claude, Gemini, local) fall back to o200k_base.
     The ratio-based noise_ratio metric is valid as long as numerator
     and denominator use the same tokenizer within a run.

2. Cache encoder instances (field practice: RAGAS, LlamaIndex, MIRAGE).
   tiktoken.get_encoding() has internal caching, but we cache at our
   level too for clarity and to avoid repeated model-name lookups.

3. Use disallowed_special=() to treat special tokens as regular text.
   Fetched web content may contain sequences that look like special
   tokens (<|endoftext|> etc). Without this flag, tiktoken raises
   ValueError. RAGAS does the same.

4. Always tokenize the full serialized string, never sum per-chunk
   counts. BPE merges happen across chunk boundaries, causing 5-15%
   error when summing individual chunk counts. Our metrics.py already
   calls serialize_chunks() first — this module reinforces that pattern
   by not exposing a "count tokens for a chunk" helper.
"""

from __future__ import annotations

import tiktoken

# ---------------------------------------------------------------------------
# Encoder cache
# ---------------------------------------------------------------------------

_encoder_cache: dict[str, tiktoken.Encoding] = {}

# The default encoding for unknown models. o200k_base is the current
# standard (GPT-4o era). cl100k_base is deprecated but still functional.
DEFAULT_ENCODING = "o200k_base"


def _get_encoder(model: str | None = None) -> tiktoken.Encoding:
    """Get a cached tiktoken encoder for the given model.

    Falls back to o200k_base for unknown models (Claude, Gemini, local,
    or None). The fallback is documented and recorded in RunResult so
    consumers know which tokenizer was used.
    """
    cache_key = model or DEFAULT_ENCODING

    if cache_key not in _encoder_cache:
        if model is not None:
            try:
                _encoder_cache[cache_key] = tiktoken.encoding_for_model(model)
            except KeyError:
                # Unknown model (Claude, Gemini, local) — fall back
                _encoder_cache[cache_key] = tiktoken.get_encoding(DEFAULT_ENCODING)
        else:
            _encoder_cache[cache_key] = tiktoken.get_encoding(DEFAULT_ENCODING)

    return _encoder_cache[cache_key]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def count_tokens(text: str, model: str | None = None) -> int:
    """Count tokens in text using the appropriate encoder.

    This is the single source of truth for token counting in the
    benchmark. Every metric, every score, every comparison flows through
    here.

    Args:
        text: The string to tokenize. Typically the full serialized
              context from serializer.serialize_chunks(), NOT individual
              chunks (see BPE boundary problem above).
        model: The model name for encoder selection. None uses the
               default (o200k_base). Passed from RunResult.answer_model
               so the tokenizer matches the model being evaluated.
    """
    encoder = _get_encoder(model)
    # disallowed_special=() treats special-token-like sequences as
    # regular text. Web content may contain <|endoftext|> etc.
    return len(encoder.encode(text, disallowed_special=()))


def encode(text: str, model: str | None = None) -> list[int]:
    """Encode text to token IDs. Used by find_answer_span for precise
    token-level span measurement."""
    encoder = _get_encoder(model)
    return encoder.encode(text, disallowed_special=())


def get_encoding_name(model: str | None = None) -> str:
    """Return the encoding name for metadata/reproducibility logging."""
    encoder = _get_encoder(model)
    return encoder.name
