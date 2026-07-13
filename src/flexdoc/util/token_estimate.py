"""Dependency-free approximate LLM token estimates based on logical-word volume."""

from __future__ import annotations

from math import ceil, isfinite

from flexdoc.util.word_count import logical_word_count

TOKENS_PER_LOGICAL_WORD = 1.6
"""
Default calibrated for o200k-family tokenizers; dense machine formats may need a larger
factor. For hard context limits, use the target model's tokenizer.
"""


def estimate_tokens(text: str, tokens_per_logical_word: float = TOKENS_PER_LOGICAL_WORD) -> int:
    """
    Estimate LLM tokens without loading a model-specific tokenizer.

    The estimate scales `logical_word_count()` by a model-family factor. Calibrate that
    factor for the target model and content when tighter bounds are needed.
    """
    if not isfinite(tokens_per_logical_word) or tokens_per_logical_word <= 0:
        raise ValueError("tokens_per_logical_word must be a positive finite number")
    return ceil(logical_word_count(text) * tokens_per_logical_word)
