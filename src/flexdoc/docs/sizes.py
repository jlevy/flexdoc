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
    matches `raw_words` for ordinary non-wide prose averaging 3–6 non-whitespace
    characters per word. Wide/fullwidth characters contribute 0.5 each; an average
    above six increases the count, one below three decreases it, and the HTML plain-text
    projection excludes non-visible markup before either word measure is computed.
    """

    lines = "lines"
    bytes = "bytes"
    chars = "chars"
    raw_words = "raw_words"
    """Whitespace-delimited words after converting HTML to plain text."""
    words = "words"
    """Logical word-equivalent volume after converting HTML to plain text."""
    wordtoks = "wordtoks"
    paragraphs = "paragraphs"
    sentences = "sentences"
    tokens = "tokens"
    """Estimated LLM token count (heuristic, no tokenizer). See `estimate_tokens`."""


def size(text: str, unit: TextUnit) -> int:
    """
    Measure `text` in `unit` after any unit-specific normalization.

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
        # Roughly accurate for HTML, text, or Markdown docs.
        return raw_word_count(html_to_plaintext(text))
    elif unit == TextUnit.words:
        return logical_word_count(html_to_plaintext(text))
    elif unit == TextUnit.wordtoks:
        return size_in_wordtoks(text)
    elif unit == TextUnit.tokens:
        return estimate_tokens(text)
    else:
        raise NotImplementedError(f"Unsupported unit for string: {unit}")
