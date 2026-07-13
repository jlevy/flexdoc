"""
Language- and format-robust word metrics.

The logical-word definition and validation are documented at
https://gist.github.com/jlevy/0d6d87885f6d85f31440e58b8cfce663.
"""

from __future__ import annotations

import unicodedata
from math import floor, isfinite

MIN_CHARS_PER_LOGICAL_WORD = 3.0
"""Prevent dense short-token or symbol sequences from inflating the normalized count."""

MAX_CHARS_PER_LOGICAL_WORD = 6.0
"""Keep long unbroken code, identifiers, and URLs from collapsing to a single word."""

WIDE_CHAR_LOGICAL_WORD_WEIGHT = 0.5
"""Make unspaced wide/fullwidth scripts measurable without language-specific parsing."""

_ROUND_HALF_UP_OFFSET = 0.5
"""Python rounds ties to even, while the portable definition requires half-up rounding."""


def raw_word_count(text: str) -> int:
    """
    Return the literal whitespace-delimited measure exposed as `TextUnit.raw_words`.
    """
    return len(text.split())


def logical_word_count(
    text: str,
    minimum_chars_per_word: float = MIN_CHARS_PER_LOGICAL_WORD,
    maximum_chars_per_word: float = MAX_CHARS_PER_LOGICAL_WORD,
    wide_char_weight: float = WIDE_CHAR_LOGICAL_WORD_WEIGHT,
) -> int:
    """
    Return a word-equivalent count robust to unspaced scripts and non-prose text.

    Non-whitespace wide and fullwidth characters contribute `wide_char_weight` each.
    The remaining whitespace-delimited count is clamped to the configured average
    character bounds before the combined count is rounded half-up. This intentionally
    diverges from a raw word count for unspaced scripts; long unbroken tokens increase
    the count, while dense short-token sequences decrease it.
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
        # Ideographic space is fullwidth whitespace, so whitespace must be excluded first.
        if not char.isspace() and unicodedata.east_asian_width(char) in {"W", "F"}:
            wide_chars += 1
            # Preserve boundaries between non-wide tokens around the extracted character.
            remaining_chars.append(" ")
        else:
            remaining_chars.append(char)

    words = "".join(remaining_chars).split()
    char_count = sum(len(word) for word in words)
    minimum_word_count = char_count / maximum_chars_per_word
    maximum_word_count = char_count / minimum_chars_per_word
    clamped_words = max(minimum_word_count, min(maximum_word_count, len(words)))
    unrounded_count = wide_chars * wide_char_weight + clamped_words
    return floor(unrounded_count + _ROUND_HALF_UP_OFFSET)
