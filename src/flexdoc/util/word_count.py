from __future__ import annotations

import unicodedata
from math import floor, isfinite

MIN_CHARS_PER_LOGICAL_WORD = 3.0
"""Minimum average length used to clamp logical words for non-wide text."""

MAX_CHARS_PER_LOGICAL_WORD = 6.0
"""Maximum average length used to clamp logical words for non-wide text."""

WIDE_CHAR_LOGICAL_WORD_WEIGHT = 0.5
"""Logical-word contribution of each non-whitespace wide or fullwidth character."""

_ROUND_HALF_UP_OFFSET = 0.5
"""Offset used to round a non-negative count to the nearest integer, ties upward."""


def raw_word_count(text: str) -> int:
    """
    Count whitespace-delimited words.
    """
    return len(text.split())


def logical_word_count(
    text: str,
    minimum_chars_per_word: float = MIN_CHARS_PER_LOGICAL_WORD,
    maximum_chars_per_word: float = MAX_CHARS_PER_LOGICAL_WORD,
    wide_char_weight: float = WIDE_CHAR_LOGICAL_WORD_WEIGHT,
) -> int:
    """
    Count normalized word-equivalent units across text formats and languages.

    Non-whitespace wide and fullwidth characters contribute `wide_char_weight` each.
    The remaining whitespace-delimited count is clamped to the configured average
    character bounds, then the combined non-negative count is rounded half-up. With
    the defaults, non-wide text matches a raw count when it averages 3–6 non-whitespace
    characters per word; longer averages increase the count and shorter averages
    decrease it.
    """
    if not isfinite(minimum_chars_per_word) or minimum_chars_per_word <= 0:
        raise ValueError("minimum_chars_per_word must be a positive finite number")
    if not isfinite(maximum_chars_per_word) or maximum_chars_per_word <= 0:
        raise ValueError("maximum_chars_per_word must be a positive finite number")
    if maximum_chars_per_word < minimum_chars_per_word:
        raise ValueError("maximum_chars_per_word must be at least minimum_chars_per_word")
    if not isfinite(wide_char_weight) or wide_char_weight < 0:
        raise ValueError("wide_char_weight must be a non-negative finite number")

    wide_chars = 0
    remaining_chars: list[str] = []
    for char in text:
        if not char.isspace() and unicodedata.east_asian_width(char) in {"W", "F"}:
            wide_chars += 1
            remaining_chars.append(" ")
        else:
            remaining_chars.append(char)

    words = "".join(remaining_chars).split()
    char_count = sum(len(word) for word in words)
    clamped_words = max(
        char_count / maximum_chars_per_word,
        min(char_count / minimum_chars_per_word, len(words)),
    )
    unrounded_count = wide_chars * wide_char_weight + clamped_words
    return floor(unrounded_count + _ROUND_HALF_UP_OFFSET)
