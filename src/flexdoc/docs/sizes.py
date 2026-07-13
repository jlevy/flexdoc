from enum import StrEnum

from flexdoc.docs.wordtoks import wordtokenize
from flexdoc.html.html_plaintext import html_to_plaintext
from flexdoc.util.token_estimate import estimate_tokens
from flexdoc.util.word_count import logical_word_count, raw_word_count


def size_in_bytes(text: str) -> int:
    return len(text.encode("utf-8"))


def size_in_wordtoks(text: str) -> int:
    return len(wordtokenize(text))


class TextUnit(StrEnum):
    """
    Text units of measure.

    `words` is a normalized logical-word count, not a literal whitespace split. It
    matches `raw_words` for typical non-wide prose. Long unbroken code, identifiers,
    and URLs increase it; dense short-token sequences decrease it; and unspaced
    wide/fullwidth scripts are measured per character. Both word units exclude
    non-visible HTML markup before counting.
    """

    lines = "lines"
    bytes = "bytes"
    chars = "chars"
    raw_words = "raw_words"
    words = "words"
    wordtoks = "wordtoks"
    paragraphs = "paragraphs"
    sentences = "sentences"
    tokens = "tokens"
    """Estimated LLM token count (heuristic, no tokenizer). See `estimate_tokens`."""


def size(text: str, unit: TextUnit) -> int:
    """
    Measure `text`, projecting HTML to plain text only for word units.

    `TextUnit.words` uses logical-word semantics described on `TextUnit`; use
    `TextUnit.raw_words` for a literal whitespace-delimited count.
    """
    if unit == TextUnit.lines:
        return len(text.splitlines())
    elif unit == TextUnit.bytes:
        return size_in_bytes(text)
    elif unit == TextUnit.chars:
        return len(text)
    elif unit == TextUnit.raw_words:
        return raw_word_count(html_to_plaintext(text))
    elif unit == TextUnit.words:
        return logical_word_count(html_to_plaintext(text))
    elif unit == TextUnit.wordtoks:
        return size_in_wordtoks(text)
    elif unit == TextUnit.tokens:
        return estimate_tokens(text)
    else:
        raise NotImplementedError(f"Unsupported unit for string: {unit}")
