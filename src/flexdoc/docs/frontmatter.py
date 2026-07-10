"""
Detection of leading YAML frontmatter, at the string level.

`frontmatter-format` (the library) is file-based — every `fmf_*` function takes a path —
so it cannot parse an in-memory string and is unusable in `FlexDoc.from_text(str)`. This
module detects the leading `---`-delimited block itself, matching `frontmatter-format`'s
`FmStyle.yaml` delimiters (an opening `---` line and a closing `---` line), without any
file I/O.
"""

from __future__ import annotations

_DELIM = "---"


def _is_delimiter_line(line: str) -> bool:
    """Match `---` with trailing horizontal whitespace or a CR, never leading whitespace."""
    return line.rstrip(" \t\r") == _DELIM


def split_frontmatter(text: str) -> tuple[str | None, int]:
    """
    Split a leading YAML frontmatter block from `text`.

    Returns `(raw, content_offset)` where `raw` is the verbatim block — both delimiter
    lines and the trailing newline included — or `None` when there is no frontmatter, and
    `text[content_offset:]` is the body (`content_offset == 0` when absent).

    Frontmatter must begin at offset 0 with a `---` line and be closed by a later `---`
    line. Both delimiters tolerate trailing spaces and tabs but reject leading
    whitespace. A leading delimiter with no matching closing line is an ordinary
    thematic break, not frontmatter, and yields `(None, 0)`.
    """
    first_nl = text.find("\n")
    if first_nl == -1:
        return None, 0
    if not _is_delimiter_line(text[:first_nl]):
        return None, 0

    pos = first_nl + 1
    while pos <= len(text):
        nl = text.find("\n", pos)
        line_end = len(text) if nl == -1 else nl
        if _is_delimiter_line(text[pos:line_end]):
            content_offset = len(text) if nl == -1 else nl + 1
            return text[:content_offset], content_offset
        if nl == -1:
            break
        pos = nl + 1
    return None, 0


## Tests


def test_split_frontmatter():
    # Standard block, blank line before body.
    raw, off = split_frontmatter("---\ntitle: Hello\ntags: [a, b]\n---\n\n# Body\n")
    assert raw == "---\ntitle: Hello\ntags: [a, b]\n---\n"
    assert off == len(raw)

    # Body immediately after the close (no blank line).
    raw, off = split_frontmatter("---\ntitle: x\n---\n# Body now\n")
    assert raw == "---\ntitle: x\n---\n"
    assert off == len("---\ntitle: x\n---\n")

    # Empty frontmatter.
    assert split_frontmatter("---\n---\nbody\n") == ("---\n---\n", 8)

    # CRLF input.
    raw, off = split_frontmatter("---\r\ntitle: x\r\n---\r\nbody\r\n")
    assert raw == "---\r\ntitle: x\r\n---\r\n"
    assert off == len(raw)

    # No frontmatter.
    assert split_frontmatter("# Heading\n\nBody.\n") == (None, 0)

    # A leading thematic break with no closing delimiter is NOT frontmatter.
    assert split_frontmatter("---\n\nJust a rule above.\n") == (None, 0)

    # Must start at offset 0.
    assert split_frontmatter("\n---\ntitle: x\n---\nbody\n") == (None, 0)

    # Trailing horizontal whitespace is accepted and preserved verbatim.
    spaced = "--- \t\ntitle: x\n---\t \nbody\n"
    raw = spaced[: spaced.index("body")]
    assert split_frontmatter(spaced) == (raw, len(raw))

    # Leading whitespace still disqualifies either delimiter.
    assert split_frontmatter(" ---\ntitle: x\n---\nbody\n") == (None, 0)
    assert split_frontmatter("---\ntitle: x\n ---\nbody\n") == (None, 0)

    # A whitespace-suffixed opening delimiter without a close remains a thematic break.
    assert split_frontmatter("--- \t\n\nJust a rule above.\n") == (None, 0)
