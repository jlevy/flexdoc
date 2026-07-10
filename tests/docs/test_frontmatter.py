"""
Frontmatter isolation (editing view): a leading YAML block is a non-content region,
excluded from paragraphs/sentences/size and exposed through `FlexDoc.frontmatter`, while
`source_text` keeps the full normalized source and spans stay absolute. Detector unit
tests live inline in `flexdoc.docs.frontmatter`; structural-view exclusion is tested
separately.
"""

from __future__ import annotations

from textwrap import dedent

from flexdoc.docs import FlexDoc
from flexdoc.docs.debug import doc_report_data
from flexdoc.docs.node import NodeKind
from flexdoc.docs.sizes import TextUnit

_FM = "---\ntitle: Hello\ntags: [a, b]\n---\n\n"
_BODY = (
    dedent("""
    # Heading

    First paragraph with some words.

    Second paragraph here.
    """).strip()
    + "\n"
)


def test_frontmatter_property_and_paragraph_exclusion():
    doc = FlexDoc.from_text(_FM + _BODY)
    assert doc.frontmatter == "---\ntitle: Hello\ntags: [a, b]\n---\n"
    assert doc.source_text == _FM + _BODY  # full original retained
    content_offset = len(_FM)
    assert all(p.span[0] >= content_offset for p in doc.paragraphs)
    assert all("title: Hello" not in p.original_text for p in doc.paragraphs)


def test_frontmatter_excluded_from_size():
    with_fm = FlexDoc.from_text(_FM + _BODY)
    body_only = FlexDoc.from_text(_BODY)
    for unit in (TextUnit.words, TextUnit.wordtoks):
        assert with_fm.size(unit) == body_only.size(unit)


def test_span_roundtrip_invariant_holds_with_frontmatter():
    doc = FlexDoc.from_text(_FM + _BODY)
    for p in doc.paragraphs:
        assert doc.source_text[p.span[0] : p.span[1]] == p.original_text


def test_thematic_break_is_not_frontmatter():
    # A leading `---` with no closing delimiter is a thematic break, not frontmatter.
    doc = FlexDoc.from_text("---\n\n# Real Heading\n\nBody.\n")
    assert doc.frontmatter is None
    assert doc.source_text == "---\n\n# Real Heading\n\nBody.\n"


def test_frontmatter_excluded_from_structural_views():
    doc = FlexDoc.from_text(_FM + _BODY)
    co = len(_FM)
    assert doc.blocks() and all(b.span[0] >= co for b in doc.blocks())
    assert doc.sections() and all(s.span[0] >= co for s in doc.sections())
    assert all(bb.block.span[0] >= co for bb in doc.base_blocks())
    table = doc.node_table()
    assert all(n.source_span is None or n.source_span[0] >= co for n in table.nodes.values())


def test_yaml_frontmatter_is_not_a_section():
    # `title: Hello\n---` can parse as a setext H2; it must not become a document section.
    doc = FlexDoc.from_text(_FM + _BODY)
    assert [s.title for s in doc.sections()] == ["Heading"]


def test_body_blocks_unperturbed_by_frontmatter():
    co = len(_FM)
    with_fm = FlexDoc.from_text(_FM + _BODY).blocks()
    body_only = FlexDoc.from_text(_BODY).blocks()
    assert [b.type for b in with_fm] == [b.type for b in body_only]
    # Same structure, spans shifted by exactly the frontmatter length.
    assert [b.span for b in with_fm] == [(s + co, e + co) for s, e in (b.span for b in body_only)]


def test_frontmatter_links_are_not_content_links():
    fm = "---\ntitle: [Meta](https://meta.example)\n[ref]: https://front.example\n---\n\n"
    body = (
        "See [Body](https://body.example), [Unresolved][ref], and [Resolved][bodyref].\n\n"
        "[bodyref]: https://bodyref.example\n"
    )
    doc = FlexDoc.from_text(fm + body)

    links = doc.links()
    assert {link.url for link in links} == {
        "https://body.example",
        "https://bodyref.example",
    }
    assert all(link.span is None or link.span[0] >= len(fm) for link in links)

    table = doc.node_table()
    link_nodes = [n for n in table.nodes.values() if n.kind == NodeKind.link]
    urls: set[str] = set()
    for node in link_nodes:
        url = node.attrs["url"]
        assert isinstance(url, str)
        urls.add(url)
    assert urls == {
        "https://body.example",
        "https://bodyref.example",
    }
    assert all(n.source_span is None or n.source_span[0] >= len(fm) for n in link_nodes)


def test_body_bare_url_does_not_reuse_matching_frontmatter_text():
    url = "https://same.example"
    fm = f"---\nsource: {url}\n---\n\n"
    body = f"Visit {url} for details.\n"
    doc = FlexDoc.from_text(fm + body)

    links = doc.links()
    assert len(links) == 1
    expected_start = len(fm) + body.index(url)
    assert links[0].span == (expected_start, expected_start + len(url))


def test_doc_report_base_blocks_exclude_frontmatter():
    doc = FlexDoc.from_text(_FM + _BODY)
    report = doc_report_data(doc)
    rows = report["base_blocks"]["blocks"]
    texts = [row["text"] for row in rows]
    assert texts
    assert "---" not in texts
    assert all("title: Hello" not in text for text in texts)
    assert report["base_blocks"]["cover_ok"]
    assert report["base_blocks"]["uncovered_nonspace"] == 0


def test_frontmatter_markdown_constructs_cannot_leak_into_body():
    # A YAML block scalar containing a code fence must not open a fenced block that
    # swallows the body (the frontmatter region is blanked out of the shared parse).
    doc = FlexDoc.from_text("---\ncode: |\n  ```\n---\n\n# Heading\n\nParagraph.\n")
    types = [b.type.value for b in doc.blocks()]
    assert types == ["heading", "paragraph"]
    assert len(doc.sections()) == 1
    assert doc.sections()[0].title == "Heading"
    assert doc.prose_text() == "Heading\n\nParagraph."

    # Same guarantee for the base-block partition and the node table.
    assert [bb.block.type.value for bb in doc.base_blocks()] == ["heading", "paragraph"]
    heading_nodes = doc.node_table().by_kind(NodeKind.heading)
    assert len(heading_nodes) == 1
