from math import ceil

from flexdoc import FlexDoc
from flexdoc.docs import SentIndex
from flexdoc.docs.sizes import TextUnit, size
from flexdoc.util import (
    TOKENS_PER_LOGICAL_WORD,
    estimate_tokens,
    logical_word_count,
    raw_word_count,
)


def test_logical_word_count_matches_raw_count_for_ordinary_prose():
    text = "This is a simple sentence with nine common words."
    assert raw_word_count(text) == 9
    assert logical_word_count(text) == raw_word_count(text)


def test_logical_word_count_weights_nonwhitespace_wide_characters():
    assert logical_word_count("你好世界") == 2
    assert logical_word_count("你") == 1
    assert logical_word_count("\u3000\u3000") == 0


def test_logical_word_count_clamps_symbolic_and_short_token_text():
    formula = "a+b*clamp(x,lo,hi)"
    assert raw_word_count(formula) == 1
    assert logical_word_count(formula) == 3
    assert logical_word_count("a b c d e f") == 2
    assert logical_word_count("你好 abcdefghijkl") == 3


def test_logical_word_count_handles_empty_and_long_unbroken_text():
    url = "https://example.com/really-long-path?query=value&other=two"
    assert logical_word_count("") == 0
    assert raw_word_count(url) == 1
    assert logical_word_count(url) > raw_word_count(url)


def test_logical_word_count_supports_custom_bounds_and_wide_weight():
    assert logical_word_count("你好", wide_char_weight=1.0) == 2
    assert (
        logical_word_count("abcdefghij", minimum_chars_per_word=2.0, maximum_chars_per_word=10.0)
        == 1
    )


def test_logical_word_count_rejects_invalid_configuration():
    cases = [
        (
            lambda: logical_word_count("text", minimum_chars_per_word=0),
            "minimum_chars_per_word",
        ),
        (
            lambda: logical_word_count("text", minimum_chars_per_word=4, maximum_chars_per_word=3),
            "maximum_chars_per_word",
        ),
        (lambda: logical_word_count("text", wide_char_weight=-0.5), "wide_char_weight"),
    ]
    for call, expected_name in cases:
        try:
            call()
        except ValueError as error:
            assert expected_name in str(error)
        else:
            raise AssertionError(f"Expected invalid {expected_name} to raise ValueError")


def test_text_units_distinguish_raw_and_logical_plaintext_words():
    text = "<p>你好世界</p>"
    assert "words" not in {unit.value for unit in TextUnit}
    assert size(text, TextUnit.raw_words) == 1
    assert size(text, TextUnit.logical_words) == 2


def test_document_logical_words_round_once_across_all_paragraphs():
    doc = FlexDoc.from_text("a.\n\nb.\n\nc.")
    assert doc.size(TextUnit.logical_words) == logical_word_count(doc.reassemble()) == 2
    assert sum(paragraph.size(TextUnit.logical_words) for paragraph in doc.paragraphs) == 3


def test_section_sizes_and_tree_default_to_logical_words():
    doc = FlexDoc.from_text("# T\n\n你好世界你好世界")
    section = doc.sections()[0]
    assert section.size(TextUnit.raw_words) == 3
    assert section.size(TextUnit.logical_words) == 5
    assert doc.section_size_tree() == "# T  (5 logical_words)"
    assert "5 logical words" in doc.size_summary()


def test_seek_to_sent_supports_both_word_units():
    doc = FlexDoc.from_text("This is the first sentence. This is the second sentence.")
    for unit in (TextUnit.raw_words, TextUnit.logical_words):
        assert doc.seek_to_sent(5, unit) == (SentIndex(0, 1), 5)


def test_estimate_tokens_scales_logical_words_across_text_forms():
    for text in (
        "This is ordinary English prose with common words.",
        "你好世界你好世界",
        "a+b*clamp(x,lo,hi)",
    ):
        assert estimate_tokens(text) == ceil(logical_word_count(text) * TOKENS_PER_LOGICAL_WORD)


def test_estimate_tokens_validates_custom_multiplier():
    assert estimate_tokens("", tokens_per_logical_word=2.0) == 0
    assert estimate_tokens("你好", tokens_per_logical_word=2.0) == 2
    for invalid_multiplier in (0.0, -1.0, float("inf"), float("nan")):
        try:
            estimate_tokens("text", tokens_per_logical_word=invalid_multiplier)
        except ValueError as error:
            assert "tokens_per_logical_word" in str(error)
        else:
            raise AssertionError(f"Expected invalid multiplier {invalid_multiplier} to raise")
