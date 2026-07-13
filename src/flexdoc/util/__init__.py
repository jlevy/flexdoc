# flake8: noqa: F401

from flexdoc.util.read_time import DEFAULT_WORDS_PER_MINUTE, format_read_time
from flexdoc.util.token_estimate import TOKENS_PER_LOGICAL_WORD, estimate_tokens
from flexdoc.util.word_count import (
    MAX_CHARS_PER_LOGICAL_WORD,
    MIN_CHARS_PER_LOGICAL_WORD,
    WIDE_CHAR_LOGICAL_WORD_WEIGHT,
    logical_word_count,
    raw_word_count,
)

__all__ = [
    "MAX_CHARS_PER_LOGICAL_WORD",
    "MIN_CHARS_PER_LOGICAL_WORD",
    "WIDE_CHAR_LOGICAL_WORD_WEIGHT",
    "format_read_time",
    "DEFAULT_WORDS_PER_MINUTE",
    "TOKENS_PER_LOGICAL_WORD",
    "estimate_tokens",
    "logical_word_count",
    "raw_word_count",
]
