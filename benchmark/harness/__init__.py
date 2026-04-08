"""Shared evaluation harness — runs any baseline against any query set.

Three modules:
- types.py    — the contract every baseline must satisfy
- metrics.py  — noise_ratio (cost) and answer_accuracy (quality)
- judge.py    — LLM-as-judge for semantic equivalence (accuracy fallback)
- runner.py   — composes baseline + query set + metrics into a Result
"""
