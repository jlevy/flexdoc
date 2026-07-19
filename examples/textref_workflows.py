"""
Compose TextRefs across extraction, retrieval, citation, annotation, and edit workflows.

Run from the repository checkout with: `uv run python examples/textref_workflows.py`
"""

from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent

from flexdoc import AnnotationSet, FlexDoc, TextAnnotation, TextBody, TextRef

_SOURCE = dedent("""
    # Findings

    Revenue increased by 12 percent in 2025.

    The filing attributes growth to subscription renewals.

    # Risks

    Customer concentration remains material.
    """).strip()


@dataclass(frozen=True)
class ExtractedValue:
    """A consumer-owned result retaining one or more source references."""

    value: str
    source_refs: tuple[TextRef, ...]


@dataclass(frozen=True)
class SuggestedEdit:
    """A consumer-owned edit proposal; FlexDoc only resolves its target."""

    target: TextRef
    replacement: str


def main() -> None:
    doc = FlexDoc.from_text(_SOURCE)
    refs = doc.references(document="reports/2025.md")

    finding = doc.paragraphs[1]
    explanation = doc.paragraphs[2]
    extracted = ExtractedValue(
        value="Revenue grew 12 percent, attributed to subscription renewals.",
        source_refs=(refs.for_target(finding), refs.for_target(explanation)),
    )

    context = refs.context(extracted.source_refs[0], before_lines=1, after_lines=1)
    assert context.selected_source == finding.original_text
    citation_uris = tuple(source_ref.to_uri() for source_ref in extracted.source_refs)
    assert all(TextRef.from_uri(uri) in extracted.source_refs for uri in citation_uris)

    annotation = TextAnnotation(
        id="finding-1",
        target=extracted.source_refs[0],
        motivations=["classifying"],
        body=TextBody(type="text", value="Material year-over-year growth."),
        tags=["revenue", "growth"],
        captured_text=finding.original_text,
    )
    sidecar = AnnotationSet.from_annotations([annotation])
    assert AnnotationSet.from_yaml(sidecar.to_yaml()) == sidecar

    graph = doc.graph(document="reports/2025.md", annotations=sidecar)
    assert graph.schema_ == "DocGraph/v0.2"
    assert graph.source.document == refs.document
    assert graph.annotations == sidecar.annotations

    edit = SuggestedEdit(
        target=refs.for_target(doc.paragraphs[-1]),
        replacement="Customer concentration remains a material risk.",
    )
    assert refs.resolve(edit.target).resolved

    print("Citations:")
    for uri in citation_uris:
        print(f"- {uri}")
    print()
    print(refs.render_annotations(sidecar), end="")


if __name__ == "__main__":
    main()
