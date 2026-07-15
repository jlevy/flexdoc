from __future__ import annotations

from pathlib import Path

from flexdoc.docs import (
    AnnotationSet,
    DocRef,
    FlexDoc,
    HeadingAnchor,
    SpanSelector,
    TextAnnotation,
    TextBody,
    TextRef,
)

GOLDEN_PATH = Path(__file__).resolve().parent.parent / "golden/expected/textref-annotations.md"

SOURCE = "# Alpha\n\nFirst target.\n\nSecond target.\n\n# Omega\n\nEnd."


def test_single_textref_render_is_compact_and_bounded():
    doc = FlexDoc.from_text(SOURCE)
    refs = doc.references("design.md")
    start = SOURCE.index("First")
    rendered = refs.render_context(
        refs.for_span(start, start + len("First target.")),
        before_lines=1,
        after_lines=1,
    )

    assert rendered.startswith('# TextRef\n\nDocument: "design.md"')
    assert "Resolution: resolved via source_position" in rendered
    assert "Range: L3:C1-L3:C14" in rendered
    assert 'Quote: "First target."' in rendered
    assert "    3 | First target." in rendered


def test_annotation_render_golden_covers_merged_and_unresolved_groups():
    doc = FlexDoc.from_text(SOURCE)
    refs = doc.references("design.md")
    first = SOURCE.index("First")
    second = SOURCE.index("Second")
    annotations = [
        TextAnnotation(
            id="a-first",
            target=refs.for_span(first, first + len("First target.")),
            motivations=["commenting"],
            body=TextBody(type="text", value="First note."),
        ),
        TextAnnotation(
            id="a-second",
            target=refs.for_point(second, affinity="after"),
            motivations=["bookmarking"],
            body=TextBody(type="text", value="Insertion point."),
        ),
        TextAnnotation(
            id="missing",
            target=TextRef(
                format="textref/0.1",
                document=DocRef("design.md"),
                selector=SpanSelector(type="span", exact="absent"),
            ),
            motivations=["commenting"],
        ),
        TextAnnotation(
            id="ambiguous",
            target=TextRef(
                format="textref/0.1",
                document=DocRef("design.md"),
                selector=SpanSelector(type="span", exact="target"),
            ),
            motivations=["classifying"],
        ),
        TextAnnotation(
            id="orphan",
            target=refs.for_span(0, 7).model_copy(update={"document": DocRef("other.md")}),
            motivations=["commenting"],
        ),
    ]

    rendered = refs.render_annotations(annotations, before_lines=1, after_lines=1)
    assert rendered == GOLDEN_PATH.read_text()
    assert rendered.count("## Lines") == 1
    assert "## Missing" in rendered
    assert "## Ambiguous" in rendered
    assert "## Orphaned" in rendered


def test_annotation_set_render_and_quote_elision_are_deterministic():
    source = "# Heading\n\n" + "x" * 100
    doc = FlexDoc.from_text(source)
    refs = doc.references("long.md")
    annotation = TextAnnotation(
        id="long",
        target=refs.for_span(source.index("x"), len(source)),
        motivations=["commenting"],
    )
    sidecar = AnnotationSet.from_annotations([annotation])
    first = refs.render_annotations(sidecar, max_quote_chars=40)
    second = refs.render_annotations(sidecar, max_quote_chars=40)
    assert first == second
    assert "chars elided" in first


def test_render_exposes_boundary_mismatch_and_source_mismatch():
    doc = FlexDoc.from_text(SOURCE)
    refs = doc.references("design.md")
    section_ref = refs.for_section(doc.sections()[0])
    assert section_ref.selector is not None
    stale_section = section_ref.model_copy(
        update={
            "selector": section_ref.selector.model_copy(
                update={"end_anchor": HeadingAnchor(exact="# Missing")}
            )
        }
    )
    stale_hash = refs.for_span(0, 7).model_copy(update={"source_hash": "sha256:" + "0" * 64})
    rendered = refs.render_annotations(
        [
            TextAnnotation(id="boundary", target=stale_section, motivations=["commenting"]),
            TextAnnotation(id="stale", target=stale_hash, motivations=["commenting"]),
        ]
    )
    assert "## Boundary mismatched" in rendered
    assert "Source validation: mismatched" in rendered
