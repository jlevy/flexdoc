"""
Contract for the package-root API surface. The root surface grows only deliberately,
so this pins both the identity of each export and the exact set.

The surface was decided against the two known downstream users: chopdiff (imports
dominated by `FlexDoc`, `TextUnit`, `BlockType`) and practical-prose-style document
evaluation (metrics over the textual layer, `SpanRef` annotation of exact sentences,
`DocGraph`/`Detail` for source-linked UI rendering).
"""

from __future__ import annotations

import flexdoc
import flexdoc.docs


def test_root_exports_are_the_canonical_objects():
    assert flexdoc.FlexDoc is flexdoc.docs.FlexDoc
    assert flexdoc.DocGraph is flexdoc.docs.DocGraph
    assert flexdoc.Detail is flexdoc.docs.Detail
    assert flexdoc.SpanRef is flexdoc.docs.SpanRef
    assert flexdoc.BlockType is flexdoc.docs.BlockType
    assert flexdoc.NodeKind is flexdoc.docs.NodeKind
    assert flexdoc.Layer is flexdoc.docs.Layer
    assert flexdoc.TextUnit is flexdoc.docs.TextUnit
    assert flexdoc.DocRef is flexdoc.docs.DocRef
    assert flexdoc.TextRef is flexdoc.docs.TextRef
    assert flexdoc.TextRefContext is flexdoc.docs.TextRefContext
    assert flexdoc.TextRefResolution is flexdoc.docs.TextRefResolution


def test_root_surface_is_deliberate():
    assert sorted(flexdoc.__all__) == [
        "BlockType",
        "Detail",
        "DocGraph",
        "DocRef",
        "FlexDoc",
        "Layer",
        "NodeKind",
        "SpanRef",
        "TextRef",
        "TextRefContext",
        "TextRefResolution",
        "TextRefTargetKind",
        "TextUnit",
    ]
    assert not hasattr(flexdoc, "resolve")
    assert not hasattr(flexdoc, "resolve_and_update")
    assert not hasattr(flexdoc.docs, "resolve")
    assert not hasattr(flexdoc.docs, "resolve_and_update")


def test_docs_surface_promotes_the_document_model_only():
    assert sorted(flexdoc.docs.__all__) == [
        "BaseBlock",
        "Block",
        "BlockType",
        "CodeInfo",
        "DEFAULT_INCLUDE",
        "Detail",
        "DocGraph",
        "DocRef",
        "DocumentStatus",
        "FlexDoc",
        "HeadingAnchor",
        "HeadingInfo",
        "LAYER_NESTING",
        "Layer",
        "Link",
        "LinkForm",
        "ListInfo",
        "NAVIGABLE_LINK_FORMS",
        "NestingGuarantee",
        "Node",
        "NodeKind",
        "NodeModel",
        "NodeTable",
        "Offsets",
        "Paragraph",
        "PointAffinity",
        "PointSelector",
        "ResolutionMethod",
        "Section",
        "SectionSelector",
        "SelectorStatus",
        "SentIndex",
        "Sentence",
        "SourceInfo",
        "SourceRange",
        "SourceValidation",
        "SpanRef",
        "SpanSelector",
        "TableInfo",
        "TextRef",
        "TextRefContext",
        "TextRefResolution",
        "TextRefTargetError",
        "TextRefTargetKind",
        "TextUnit",
        "Views",
        "base_blocks",
        "block_type_for",
        "build_doc_graph",
        "build_node_table",
        "collect",
        "doc_graph_yaml",
        "doc_report",
        "doc_report_data",
        "dump_views",
        "normalize_source",
        "parse_blocks",
        "parse_source_span_attr",
        "render_node_attrs",
        "resolve_batch",
        "resolve_text_ref",
        "source_hash",
        "walk_blocks",
        "wrap_with_node_attrs",
    ]

    for internal_name in ("TokenDiff", "TokenMapping", "wordtokenize"):
        assert not hasattr(flexdoc.docs, internal_name)


def test_root_working_set_covers_the_common_first_lines():
    from flexdoc import FlexDoc, NodeKind, SpanRef, TextUnit

    doc = FlexDoc.from_text("# T\n\nA sentence with a [link](https://e.com). Another.\n")
    assert doc.size(TextUnit.words) > 0
    assert doc.paragraphs[0].heading_level == 1
    assert doc.paragraphs[0].heading_title == "T"
    assert doc.paragraphs[1].heading_level is None
    assert doc.paragraphs[1].heading_title is None
    links = doc.collect(kinds={NodeKind.link}, recursive=True)
    assert len(links) == 1
    # Annotating an exact sentence: build a durable ref from its span and resolve it.
    sent = doc.paragraphs[1].sentences[0]
    ref = SpanRef.from_span(doc.source_text, *sent.span)
    assert ref.resolve(doc.source_text) == sent.span

    persisted = ref.to_persisted()
    assert persisted.resolve_and_update(doc.source_text) == sent.span
    assert (persisted.start, persisted.end) == sent.span
