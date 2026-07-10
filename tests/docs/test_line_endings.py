"""
Line-ending normalization: `from_text` normalizes `\r\n` and lone `\r` to `\n` so the
editing and structural views share one offset space.
Before normalization, marko's LF-based block positions desynchronized structural
spans from a CRLF `source_text`, corrupting `blocks()`, `sections()`,
`base_blocks()`, and `prose_text()` (while the regex-based paragraph view stayed
correct), so this pins the whole-model behavior.
"""

from __future__ import annotations

from flexdoc import FlexDoc
from flexdoc.docs import BlockType

_CRLF_DOC = "# H1\r\n\r\nPara one.\r\n\r\n## H2\r\n\r\n- item a\r\n- item b\r\n\r\nMore text.\r\n"


def _assert_model_consistent(doc: FlexDoc) -> None:
    source = doc.source_text
    # Every block span slices to non-empty text with no leading/trailing whitespace.
    for block in doc.blocks():
        s, e = block.span
        text = source[s:e]
        assert text == text.strip()
        assert text
    # Base-block partition covers every non-whitespace content character exactly
    # once (frontmatter is a non-content region, outside the partition).
    covered: set[int] = set()
    for bb in doc.base_blocks():
        s, e = bb.block.span
        assert not (set(range(s, e)) & covered)
        covered.update(range(s, e))
    content_start = len(doc.frontmatter or "")
    uncovered = [
        i
        for i, c in enumerate(source)
        if i >= content_start and not c.isspace() and i not in covered
    ]
    assert uncovered == []
    # Paragraph spans round-trip.
    for para in doc.paragraphs:
        s, e = para.span
        assert source[s:e] == para.original_text


def test_crlf_input_normalized_and_consistent():
    doc = FlexDoc.from_text(_CRLF_DOC)
    assert "\r" not in doc.source_text
    _assert_model_consistent(doc)

    blocks = doc.blocks()
    types = [b.type for b in blocks]
    assert types == [
        BlockType.heading,
        BlockType.paragraph,
        BlockType.heading,
        BlockType.list,
        BlockType.paragraph,
    ]
    sections = doc.sections()
    assert len(sections) == 1
    assert sections[0].title == "H1"
    assert [c.title for c in sections[0].children] == ["H2"]
    assert doc.prose_text() == "H1\n\nPara one.\n\nH2\n\nitem a\n\nitem b\n\nMore text."


def test_crlf_equivalent_to_lf():
    lf_doc = FlexDoc.from_text(_CRLF_DOC.replace("\r\n", "\n"))
    crlf_doc = FlexDoc.from_text(_CRLF_DOC)
    assert crlf_doc.source_text == lf_doc.source_text
    assert crlf_doc.reassemble() == lf_doc.reassemble()
    assert [b.span for b in crlf_doc.blocks()] == [b.span for b in lf_doc.blocks()]


def test_lone_cr_normalized():
    doc = FlexDoc.from_text("# Title\r\rOld Mac line one.\rStill same paragraph.\r")
    assert "\r" not in doc.source_text
    _assert_model_consistent(doc)
    assert [b.type for b in doc.blocks()] == [BlockType.heading, BlockType.paragraph]


def test_crlf_frontmatter():
    doc = FlexDoc.from_text("---\r\ntitle: x\r\n---\r\n\r\n# Body\r\n\r\nText.\r\n")
    assert doc.frontmatter == "---\ntitle: x\n---\n"
    assert [b.type for b in doc.blocks()] == [BlockType.heading, BlockType.paragraph]
    _assert_model_consistent(doc)
