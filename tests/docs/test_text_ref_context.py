from __future__ import annotations

import pytest

from flexdoc.docs import (
    DocRef,
    FlexDoc,
    Node,
    NodeKind,
    PointAffinity,
    SectionSelector,
    SelectorStatus,
    SpanSelector,
    TextRef,
    TextRefTargetError,
)

SOURCE = "# Alpha\n\nFirst sentence. Second [link](https://example.com).\n\n## Child\n\nBody.\n\n# Omega\n\nEnd."


def test_reference_context_maps_public_locatable_values():
    doc = FlexDoc.from_text(SOURCE)
    refs = doc.references(document="./design.md")

    targets = [
        doc.paragraphs[0],
        doc.paragraphs[1].sentences[0],
        doc.blocks()[0],
        doc.base_blocks()[0],
        doc.links()[0],
        next(node for node in doc.node_table().nodes.values() if node.kind == NodeKind.link),
        doc.paragraphs[1].span,
    ]
    for target in targets:
        text_ref = refs.for_target(target)
        assert isinstance(text_ref.selector, SpanSelector)
        resolution = refs.resolve(text_ref)
        assert resolution.selector == SelectorStatus.resolved
        assert resolution.span is not None
        assert SOURCE[resolution.span.start : resolution.span.end] == text_ref.selector.exact

    whole = refs.whole_document()
    assert whole.selector is None
    resolution = refs.resolve(whole)
    assert resolution.span is not None
    assert resolution.span.end == len(SOURCE)


def test_sections_remain_semantic_and_resolve_to_trimmed_flexdoc_span():
    doc = FlexDoc.from_text(SOURCE)
    refs = doc.references(document=DocRef("design.md"))
    section = doc.sections()[0]
    text_ref = refs.for_target(section)

    assert isinstance(text_ref.selector, SectionSelector)
    assert text_ref.selector.start_anchor.exact == "# Alpha"
    assert text_ref.selector.end_anchor is not None
    assert text_ref.selector.end_anchor.exact == "# Omega"
    resolution = refs.resolve(text_ref)
    assert resolution.selector == SelectorStatus.resolved
    assert resolution.span is not None
    assert (resolution.span.start, resolution.span.end) == section.span

    section_node = next(
        node for node in doc.node_table().nodes.values() if node.kind == NodeKind.section
    )
    assert isinstance(refs.for_target(section_node).selector, SectionSelector)


def test_point_context_and_visible_target_failures():
    doc = FlexDoc.from_text(SOURCE)
    refs = doc.references(document="design.md")
    boundary = SOURCE.index("Second")
    point = refs.for_point(boundary, affinity=PointAffinity.after)
    assert point.selector is not None
    resolution = refs.resolve(point)
    assert resolution.span is not None
    assert resolution.span.start == boundary

    with pytest.raises(TextRefTargetError, match="not locatable"):
        refs.for_target(
            Node(
                id="external",
                kind=NodeKind.paragraph,
                layer=doc.node_table().nodes[next(iter(doc.node_table().nodes))].layer,
                parent=None,
            )
        )

    other = FlexDoc.from_text("# Other\n\nText.")
    with pytest.raises(TextRefTargetError, match="different document"):
        refs.for_target(other.sections()[0])

    with pytest.raises(TextRefTargetError, match="does not match"):
        refs.for_target(other.paragraphs[0])


def test_reference_context_rejects_ref_for_another_document():
    doc = FlexDoc.from_text(SOURCE)
    refs = doc.references(document="design.md")
    other = doc.references(document="other.md").for_span(0, 7)
    result = refs.resolve(other)
    assert result.document == "invalid"
    assert result.selector == SelectorStatus.unsupported


def test_structured_context_has_unicode_coordinates_and_bounded_lines():
    source = "zero\nalpha cafe\N{COMBINING ACUTE ACCENT}\nomega\nlast"
    doc = FlexDoc.from_text(source)
    refs = doc.references(document="unicode.md")
    start = source.index("cafe")
    context = refs.context(
        refs.for_span(start, start + len("cafe\N{COMBINING ACUTE ACCENT}")),
        before_lines=1,
        after_lines=1,
    )

    assert context.selected_source == "cafe\N{COMBINING ACUTE ACCENT}"
    assert context.start is not None
    assert (context.start.line, context.start.column) == (2, 7)
    assert context.end is not None
    assert (context.end.line, context.end.column) == (2, 12)
    assert [line.number for line in context.lines] == [1, 2, 3]
    assert context.omitted_before is False
    assert context.omitted_after is True


def test_structured_context_covers_whole_document_points_and_failures():
    doc = FlexDoc.from_text(SOURCE)
    refs = doc.references(document="design.md")

    whole = refs.context(refs.whole_document(), before_lines=0, after_lines=0)
    assert whole.selected_source == SOURCE
    assert whole.start is not None and whole.start.line == 1
    assert whole.end is not None and whole.end.offset == len(SOURCE)

    position = SOURCE.index("Second")
    point = refs.context(refs.for_point(position))
    assert point.selected_source == ""
    assert point.start == point.end

    missing_ref = TextRef(
        format="textref/0.1",
        document=DocRef("design.md"),
        selector=SpanSelector(type="span", exact="missing"),
    )
    missing = refs.context(missing_ref)
    assert missing.resolution.selector == SelectorStatus.missing
    assert missing.resolved_span is None
    assert missing.selected_source is None
    assert missing.lines == ()


def test_structured_context_reports_source_mismatch_and_validates_limits():
    doc = FlexDoc.from_text(SOURCE)
    refs = doc.references(document="design.md")
    text_ref = refs.for_span(0, 7).model_copy(update={"source_hash": "sha256:" + "0" * 64})
    context = refs.context(text_ref)
    assert context.resolution.source_validation == "mismatched"
    assert context.selected_source == "# Alpha"

    with pytest.raises(ValueError, match="before_lines"):
        refs.context(text_ref, before_lines=-1)
