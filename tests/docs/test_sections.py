from collections import Counter
from textwrap import dedent

from flexdoc.docs import FlexDoc
from flexdoc.docs.block_types import BlockType
from flexdoc.docs.sizes import TextUnit

_DOC = dedent(
    """
    # Top

    Intro paragraph of top.

    ## Sub A

    Body of A. Two sentences here.

    ## Sub B

    Body of B.

    # Top Two

    Final paragraph.
    """
).strip()


def test_sections_tree_structure():
    doc = FlexDoc.from_text(_DOC)
    secs = doc.sections()
    assert [(s.level, s.title) for s in secs] == [(1, "Top"), (1, "Top Two")]
    assert [(c.level, c.title) for c in secs[0].children] == [(2, "Sub A"), (2, "Sub B")]
    assert secs[1].children == []


def test_sections_returns_recursively_isolated_editing_views():
    doc = FlexDoc.from_text(_DOC)
    first = doc.sections()
    second = doc.sections()

    assert first[0] is not second[0]
    assert first[0].children[0] is not second[0].children[0]
    assert first[0].content[0] is not second[0].content[0]

    first[0].children.clear()
    first[0].content[0].sentences[0].text = "poisoned"
    first[0].heading.sentences[0].text = "poisoned"

    fresh = doc.sections()[0]
    assert [child.title for child in fresh.children] == ["Sub A", "Sub B"]
    assert fresh.content[0].sentences[0].text != "poisoned"
    assert fresh.heading.sentences[0].text != "poisoned"


def test_section_span_covers_heading_through_subtree():
    doc = FlexDoc.from_text(_DOC)
    top = doc.sections()[0]
    start, end = top.span
    assert _DOC[start:].startswith("# Top")
    covered = _DOC[start:end]
    assert "Body of B." in covered  # through the last subsection's content
    assert "Top Two" not in covered  # but not the next top-level section


def test_rolled_up_size_sums_subtree():
    doc = FlexDoc.from_text(_DOC)
    top = doc.sections()[0]
    own = top.size(TextUnit.raw_words, subtree=False)
    full = top.size(TextUnit.raw_words, subtree=True)
    assert full > own
    # Words are additive across blocks, so subtree == own + each child's subtree.
    assert full == own + sum(c.size(TextUnit.raw_words, subtree=True) for c in top.children)


def test_section_size_summary_distinguishes_own_content_and_subtree():
    top = FlexDoc.from_text(_DOC).sections()[0]
    assert top.size_summary(subtree=False) == (
        "30 bytes (3 lines, 2 paras, 2 sents, 6 logical words, ~8 tok)"
    )
    assert top.size_summary() == (
        "94 bytes (11 lines, 6 paras, 6 sents, 21 logical words, ~25 tok)"
    )


def test_section_blocks_are_scoped_and_in_span():
    doc = FlexDoc.from_text(_DOC)
    top = doc.sections()[0]
    types = [b.type for b in top.blocks()]
    # Top's OWN content only: its heading and intro paragraph, not Sub A/Sub B content.
    assert types == [BlockType.heading, BlockType.paragraph]
    s_start, s_end = top.span
    for b in top.blocks():
        assert s_start <= b.span[0] and b.span[1] <= s_end


def test_section_block_type_tally_per_section():
    # Per-section block-type tally is `Counter(b.type for b in section.blocks())` now that
    # the block_type_counts() convenience is removed (superseded by collect()/blocks()).
    doc = FlexDoc.from_text(_DOC)
    top = doc.sections()[0]
    assert Counter(b.type for b in top.blocks()) == {BlockType.heading: 1, BlockType.paragraph: 1}
    sub_a = top.children[0]
    assert Counter(b.type for b in sub_a.blocks()) == {BlockType.heading: 1, BlockType.paragraph: 1}


def test_block_type_tally_is_density_invariant():
    # A loose vs. tight list yields the same tally over blocks() (density invariance);
    # the tree is a pure function of source_text, so nothing is cached.
    tight = FlexDoc.from_text("# H\n\n- a\n- b\n- c")
    loose = FlexDoc.from_text("# H\n\n- a\n\n- b\n\n- c")
    assert Counter(b.type for b in tight.blocks()) == Counter(b.type for b in loose.blocks())
    assert Counter(b.type for b in tight.blocks())[BlockType.list] == 1


def test_toc_is_flat_document_order():
    doc = FlexDoc.from_text(_DOC)
    assert [(lvl, title) for lvl, title, _span in doc.toc()] == [
        (1, "Top"),
        (2, "Sub A"),
        (2, "Sub B"),
        (1, "Top Two"),
    ]


def test_section_size_tree_renders_titles_and_sizes():
    doc = FlexDoc.from_text(_DOC)
    tree = doc.section_size_tree(units=(TextUnit.raw_words,))
    for title in ("Top", "Sub A", "Sub B", "Top Two"):
        assert title in tree


def test_setext_heading_section():
    doc = FlexDoc.from_text("Title\n=====\n\nBody here.")
    secs = doc.sections()
    assert len(secs) == 1
    assert secs[0].level == 1
    assert secs[0].title == "Title"


def test_no_headings_means_no_sections():
    doc = FlexDoc.from_text("Just a paragraph. No headings here.")
    assert doc.sections() == []
    assert doc.toc() == []


def test_section_links_includes_reference_links():
    """Section.links() must see reference-style links resolved at the document level."""
    text = "# A\n\nSee [Docs][d].\n\n[d]: https://example.com/docs\n"
    doc = FlexDoc.from_text(text)
    doc_links = doc.links()
    assert len(doc_links) == 1
    assert doc_links[0].url == "https://example.com/docs"
    section_links = doc.sections()[0].links()
    # The section must include the reference link (resolved from the document).
    assert len(section_links) >= 1
    assert any(lk.url == "https://example.com/docs" for lk in section_links)


def test_section_links_include_reference_links():
    """Section.links() derives from the document-level parse, so reference-style links
    (defined in a separate block) are attributed to their section (z8b2)."""
    from flexdoc.docs import FlexDoc

    text = "# Heading\n\nSee [docs][d] for more.\n\n[d]: https://docs.example\n"
    section = FlexDoc.from_text(text).sections()[0]
    urls = {lk.url for lk in section.links()}
    assert "https://docs.example" in urls


def test_heading_inside_code_fence_is_not_a_section():
    """A '#'-prefixed line inside a fenced code block (which blank-line paragraph
    splitting can isolate) must not become a section; only the real heading counts."""
    md = dedent(
        """
        # Real

        ```
        text

        # Not a heading
        ```

        After.
        """
    ).strip()
    doc = FlexDoc.from_text(md)
    assert [title for _, title, _ in doc.toc()] == ["Real"]


def test_sections_recover_tight_and_marker_preceded_headings():
    """Regression for the sections()/toc() heading-loss bug: a heading glued below
    preceding text (tight) or preceded by a non-blank line (e.g. an HTML-comment marker)
    is no longer dropped, because sections derive from the structural heading blocks, not
    the blank-line paragraph view."""
    tight = FlexDoc.from_text("# A\nintro\n## B\nbody\n")
    assert [title for _level, title, _span in tight.toc()] == ["A", "B"]

    marker = FlexDoc.from_text("# T\n\n<!-- marker -->\n## S\n\nbody\n")
    assert [title for _level, title, _span in marker.toc()] == ["T", "S"]


def test_tight_glued_sections_own_their_content():
    """Deep fix for the section-content bug: in a fully glued document (no blank lines) a
    heading still owns exactly its own content, derived from the structural region rather
    than the blank-line paragraph view (which merges the whole document into one paragraph,
    so the body would otherwise be attributed to no section)."""
    doc = FlexDoc.from_text("# A\nintro\n## B\nbody\n")
    (a,) = doc.sections()
    (b,) = a.children
    assert (a.level, a.title, b.level, b.title) == (1, "A", 2, "B")

    assert [blk.type for blk in a.blocks()] == [BlockType.heading, BlockType.paragraph]
    assert [blk.type for blk in b.blocks()] == [BlockType.heading, BlockType.paragraph]
    a_own = "".join(p.original_text for p in a.own_paragraphs())
    b_own = "".join(p.original_text for p in b.own_paragraphs())
    assert "intro" in a_own and "body" not in a_own
    assert "body" in b_own
    # The body now counts under B, so own sizes are symmetric and the subtree is additive.
    assert a.size(TextUnit.raw_words, subtree=False) == b.size(TextUnit.raw_words, subtree=False)
    assert a.size(TextUnit.raw_words, subtree=True) == a.size(
        TextUnit.raw_words, subtree=False
    ) + b.size(TextUnit.raw_words, subtree=True)


def test_marker_preceded_section_content_is_attributed():
    """A heading preceded by a non-blank line (an HTML-comment marker) owns its content, and
    the marker belongs to the preceding section rather than being merged with the heading."""
    doc = FlexDoc.from_text("# T\n\n<!-- marker -->\n## S\n\nbody\n")
    (t,) = doc.sections()
    (s,) = t.children
    assert (t.title, s.title) == ("T", "S")
    t_own = "".join(p.original_text for p in t.own_paragraphs())
    assert "<!-- marker -->" in t_own  # the marker is owned by T (it precedes S)
    assert "## S" not in t_own  # S's heading is not part of T's content
    assert "body" in "".join(p.original_text for p in s.own_paragraphs())


def test_toc_matches_heading_block_count():
    """Every top-level structural heading block yields exactly one toc entry."""
    doc = FlexDoc.from_text(_DOC)
    headings = [b for b in doc.blocks() if b.type == BlockType.heading]
    assert len(doc.toc()) == len(headings)
