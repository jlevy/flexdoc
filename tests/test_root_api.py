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


def test_root_surface_is_deliberate():
    assert sorted(flexdoc.__all__) == [
        "BlockType",
        "Detail",
        "DocGraph",
        "FlexDoc",
        "Layer",
        "NodeKind",
        "SpanRef",
        "TextUnit",
    ]


def test_root_working_set_covers_the_common_first_lines():
    from flexdoc import FlexDoc, NodeKind, SpanRef, TextUnit

    doc = FlexDoc.from_text("# T\n\nA sentence with a [link](https://e.com). Another.\n")
    assert doc.size(TextUnit.words) > 0
    links = doc.collect(kinds={NodeKind.link}, recursive=True)
    assert len(links) == 1
    # Annotating an exact sentence: build a durable ref from its span and resolve it.
    sent = doc.paragraphs[1].sentences[0]
    ref = SpanRef.from_span(doc.source_text, *sent.span)
    from flexdoc.docs import resolve

    assert resolve(ref, doc.source_text) == sent.span
