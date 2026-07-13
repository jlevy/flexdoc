from __future__ import annotations

from math import ceil, isfinite

from flexdoc.util.word_count import logical_word_count

TOKENS_PER_LOGICAL_WORD = 1.6
"""
Approximate o200k-family tokens per logical word, used without a tokenizer or network
access.

Validation across natural languages, source code, Markdown, and machine formats found
that 1.6 is a useful center for o200k-family tokenizers. Punctuation-dense formats can
run near 2.2 tokens per logical word, while other model families use different factors.
For exact counts or hard context limits, use the target model's tokenizer.

See GitHub issue #16 and the linked logical-word-count validation for the sample data
and limitations.
"""


def estimate_tokens(text: str, tokens_per_logical_word: float = TOKENS_PER_LOGICAL_WORD) -> int:
    """
    Estimate LLM tokens from `logical_word_count()` and a model-family multiplier.

    Fast and dependency-free but approximate. Returns 0 for empty text. The default is
    centered on o200k-family tokenizers; callers may supply a positive finite factor
    calibrated for another model family.
    """
    if not isfinite(tokens_per_logical_word) or tokens_per_logical_word <= 0:
        raise ValueError("tokens_per_logical_word must be a positive finite number")
    return ceil(logical_word_count(text) * tokens_per_logical_word)
