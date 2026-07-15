from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from flexdoc.docs import (
    AnnotationSet,
    AnnotationSetEntry,
    DocGraph,
    DocGraphV2,
    DocRef,
    FlexDoc,
    SpanSelector,
    TextAnnotation,
    TextBody,
    TextRef,
)

SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent / "src/flexdoc/docs/doc_graph_v2_schema.json"
)


def _annotation(doc: FlexDoc, *, annotation_id: str = "note-1") -> TextAnnotation:
    target = doc.references("design.md").for_span(0, 7)
    return TextAnnotation(
        id=annotation_id,
        target=target,
        motivations=["commenting"],
        body=TextBody(type="text", value="Check this heading."),
        style="review",
        tags=["heading"],
        captured_text="# Alpha",
        provenance={"importer": "review-tool", "record_id": 12},
    )


def test_annotation_and_sidecar_json_yaml_round_trip():
    doc = FlexDoc.from_text("# Alpha\n\nBody.")
    annotation = _annotation(doc)
    assert TextAnnotation.model_validate_json(annotation.model_dump_json()) == annotation

    sidecar = AnnotationSet.from_annotations([annotation])
    assert sidecar.document == DocRef("design.md")
    assert sidecar.annotations[0].target == annotation.target.selector
    assert sidecar.expand() == (annotation,)
    assert AnnotationSet.model_validate_json(sidecar.model_dump_json()) == sidecar
    assert AnnotationSet.from_yaml(sidecar.to_yaml()) == sidecar


def test_annotation_validation_is_strict_and_ids_are_unique():
    doc = FlexDoc.from_text("# Alpha\n\nBody.")
    annotation = _annotation(doc)
    with pytest.raises(ValidationError):
        TextAnnotation.model_validate(
            {**annotation.model_dump(), "motivations": [], "unexpected": True}
        )

    sidecar = AnnotationSet.from_annotations([annotation])
    duplicate = sidecar.model_dump()
    duplicate["annotations"] = [duplicate["annotations"][0]] * 2
    with pytest.raises(ValidationError, match="unique"):
        AnnotationSet.model_validate(duplicate)

    detached = annotation.model_copy(
        update={"target": annotation.target.model_copy(update={"document": DocRef("other.md")})}
    )
    assert detached.target.document == DocRef("other.md")
    with pytest.raises(ValueError, match="one document"):
        AnnotationSet.from_annotations([annotation, detached])


def test_bare_sidecar_expansion_includes_whole_document_targets():
    sidecar = AnnotationSet(
        format="text-annotations/0.1",
        document=DocRef("design.md"),
        source_hash=None,
        annotations=[
            AnnotationSetEntry(
                id="summary",
                target=None,
                motivations=["summarizing"],
                body=TextBody(type="text", value="Document summary."),
            )
        ],
    )
    expanded = sidecar.expand()[0]
    assert expanded.target.selector is None
    assert expanded.target.document == DocRef("design.md")


def test_explicit_annotations_select_docgraph_v2_without_changing_v1():
    doc = FlexDoc.from_text("# Alpha\n\nBody.")
    annotation = _annotation(doc)
    sidecar = AnnotationSet.from_annotations([annotation])

    v1 = doc.graph()
    v2 = doc.graph(annotations=sidecar)
    assert type(v1) is DocGraph
    assert v1.schema_ == "DocGraph/v0.1"
    assert isinstance(v2, DocGraphV2)
    assert v2.schema_ == "DocGraph/v0.2"
    assert v2.source.document == DocRef("design.md")
    assert v2.source.source_hash == sidecar.source_hash
    assert v2.annotations == sidecar.annotations

    data = json.loads(v2.model_dump_json(by_alias=True))
    assert data["annotations"][0]["target"]["type"] == "span"
    assert "document" not in data["annotations"][0]["target"]


def test_docgraph_v2_rejects_a_sidecar_for_another_snapshot():
    doc = FlexDoc.from_text("# Alpha\n\nBody.")
    target = TextRef(
        format="textref/0.1",
        document=DocRef("design.md"),
        source_hash="sha256:" + "0" * 64,
        selector=SpanSelector(type="span", exact="# Alpha", start=0),
    )
    annotation = TextAnnotation(id="stale", target=target, motivations=["commenting"])
    sidecar = AnnotationSet.from_annotations([annotation])
    with pytest.raises(ValueError, match="source hash"):
        doc.graph(annotations=sidecar)


def test_docgraph_v2_json_schema_matches_committed_file():
    current = (
        json.dumps(DocGraphV2.model_json_schema(by_alias=True), indent=2, sort_keys=True) + "\n"
    )
    assert SCHEMA_PATH.read_text() == current
