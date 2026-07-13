from flexdoc.util import logical_word_count, raw_word_count


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
