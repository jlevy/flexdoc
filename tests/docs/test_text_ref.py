"""Behavioral contract for TextRef values and codecs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from flexdoc.docs.span_ref import SpanRef, resolve_batch
from flexdoc.docs.text_ref import (
    TEXTREF_FORMAT,
    DocRef,
    HeadingAnchor,
    PointAffinity,
    PointSelector,
    ResolutionMethod,
    SectionRange,
    SectionSelector,
    SelectorStatus,
    SourceValidation,
    SpanSelector,
    TextRef,
    TextRefTargetKind,
    normalize_source,
    resolve_text_ref,
    source_hash,
)

SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent / "src/flexdoc/docs/text_ref_schema.json"
)


def test_textref_json_and_uri_round_trip_all_target_kinds():
    refs = (
        TextRef(format=TEXTREF_FORMAT, document=DocRef("./design.md")),
        TextRef(
            format=TEXTREF_FORMAT,
            document=DocRef("./design.md"),
            source_hash="sha256:" + "a" * 64,
            selector=SpanSelector(
                type="span",
                exact="source text",
                prefix="before ",
                suffix=" after",
                start=7,
            ),
        ),
        TextRef(
            format=TEXTREF_FORMAT,
            document=DocRef("./design.md"),
            selector=PointSelector(
                type="point",
                position=7,
                affinity=PointAffinity.before,
                prefix="before",
                suffix=" after",
            ),
        ),
        TextRef(
            format=TEXTREF_FORMAT,
            document=DocRef("./design.md"),
            selector=SectionSelector(
                type="section",
                syntax="commonmark",
                start_anchor=HeadingAnchor(exact="## Design", start=12),
                end_anchor=HeadingAnchor(exact="## Later", start=90),
            ),
        ),
    )

    assert [ref.target_kind for ref in refs] == [
        TextRefTargetKind.whole_document,
        TextRefTargetKind.span,
        TextRefTargetKind.point,
        TextRefTargetKind.section,
    ]
    for ref in refs:
        assert TextRef.model_validate_json(ref.model_dump_json()) == ref
        assert TextRef.from_uri(ref.to_uri()) == ref
        assert TextRef.from_uri(ref.to_uri()).to_uri() == ref.to_uri()


def test_textref_uri_is_canonical_and_rejects_lossy_inputs():
    ref = TextRef(
        format=TEXTREF_FORMAT,
        document=DocRef("./a file.md"),
        selector=SpanSelector(type="span", exact="π source", start=3),
    )
    assert ref.to_uri() == (
        "textref:0.1?doc=.%2Fa%20file.md&type=span&exact=%CF%80%20source&start=3"
    )

    invalid = (
        "textref:0.1?doc=a&doc=b",
        "textref:0.1?doc=a&unknown=x",
        "textref:0.1?doc=a&type=span",
        "textref:0.2?doc=a",
        "textref:0.1?doc=a+b",
    )
    for uri in invalid:
        with pytest.raises(ValueError):
            TextRef.from_uri(uri)

    extended = TextRef(
        format=TEXTREF_FORMAT,
        document=DocRef("a"),
        extensions={"example:field": "value"},
    )
    with pytest.raises(ValueError):
        extended.to_uri()


def test_textref_models_reject_invalid_or_ambiguous_values():
    invalid_values = (
        lambda: TextRef.model_validate({"document": ""}),
        lambda: TextRef.model_validate(
            {"format": TEXTREF_FORMAT, "document": "a", "source_hash": "83f6d4"}
        ),
        lambda: TextRef(
            format=TEXTREF_FORMAT,
            document=DocRef("a"),
            selector=SpanSelector(type="span", exact=""),
        ),
        lambda: PointSelector.model_validate({"type": "point", "affinity": "before"}),
        lambda: PointSelector.model_validate(
            {"type": "point", "position": -1, "affinity": "after", "suffix": "x"}
        ),
        lambda: SectionSelector.model_validate(
            {
                "type": "section",
                "syntax": "html",
                "start_anchor": {"exact": "# A"},
            }
        ),
    )
    for build in invalid_values:
        with pytest.raises((ValidationError, ValueError)):
            build()

    with pytest.raises(ValidationError):
        TextRef.model_validate({"format": TEXTREF_FORMAT, "document": "a", "extra": 1})


def test_canonical_source_normalization_and_hashing():
    source = "a\r\nb\rcafé\n"
    normalized = "a\nb\ncafé\n"
    assert normalize_source(source) == normalized
    assert source_hash(source) == "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    with pytest.raises(ValueError):
        normalize_source("unpaired \ud800")


def test_textref_json_schema_matches_committed_file():
    current = json.dumps(TextRef.model_json_schema(), indent=2, sort_keys=True) + "\n"
    assert SCHEMA_PATH.read_text() == current


def test_typed_span_resolution_distinguishes_exact_outcomes():
    source = "first target, second target"
    second = source.rfind("target")
    bound = TextRef(
        format=TEXTREF_FORMAT,
        document=DocRef("doc.md"),
        source_hash=source_hash(source),
        selector=SpanSelector(type="span", exact="target", start=second),
    )
    result = resolve_text_ref(bound, source, document=DocRef("doc.md"))
    assert result.selector == SelectorStatus.resolved
    assert result.source_validation == SourceValidation.matched
    assert result.method == ResolutionMethod.source_position
    assert result.span is not None
    assert (result.span.start, result.span.end) == (second, second + len("target"))

    wrong_document = resolve_text_ref(bound, source, document=DocRef("other.md"))
    assert wrong_document.document == "invalid"
    assert wrong_document.selector == SelectorStatus.unsupported

    assert bound.selector is not None
    ambiguous = bound.model_copy(
        update={
            "source_hash": None,
            "selector": bound.selector.model_copy(update={"start": None}),
        }
    )
    result = resolve_text_ref(ambiguous, source)
    assert result.selector == SelectorStatus.ambiguous
    assert len(result.candidates) == 2

    missing = ambiguous.model_copy(update={"selector": SpanSelector(type="span", exact="absent")})
    assert resolve_text_ref(missing, source).selector == SelectorStatus.missing


def test_typed_point_resolution_uses_context_and_affinity_conservatively():
    source = "alpha boundary omega"
    position = source.index(" omega")
    ref = TextRef(
        format=TEXTREF_FORMAT,
        document=DocRef("doc.md"),
        selector=PointSelector(
            type="point",
            position=position,
            affinity=PointAffinity.before,
            prefix="boundary",
            suffix=" omega",
        ),
    )
    moved = "intro " + source
    result = resolve_text_ref(ref, moved)
    assert result.selector == SelectorStatus.resolved
    assert result.method == ResolutionMethod.point_context
    assert result.span is not None
    assert result.span.start == position + len("intro ")
    assert result.span.start == result.span.end

    inserted = moved.replace(" omega", " inserted omega")
    affinity = resolve_text_ref(ref, inserted)
    assert affinity.selector == SelectorStatus.resolved
    assert affinity.method == ResolutionMethod.point_affinity


def test_section_resolution_requires_structure_and_reports_boundary_mismatch():
    source = "## Design\n\nBody.\n\n## Later\n\nEnd."
    design_start = source.index("## Design")
    design_heading_end = design_start + len("## Design")
    later_start = source.index("## Later")
    later_heading_end = later_start + len("## Later")
    selector = SectionSelector(
        type="section",
        syntax="commonmark",
        start_anchor=HeadingAnchor(exact="## Design", start=design_start),
        end_anchor=HeadingAnchor(exact="## Later", start=later_start),
    )
    ref = TextRef(format=TEXTREF_FORMAT, document=DocRef("doc.md"), selector=selector)
    structure = (
        SectionRange(
            heading_start=design_start,
            heading_end=design_heading_end,
            section_end=later_start,
        ),
        SectionRange(
            heading_start=later_start,
            heading_end=later_heading_end,
            section_end=len(source),
        ),
    )

    unsupported = resolve_text_ref(ref, source)
    assert unsupported.selector == SelectorStatus.unsupported

    resolved = resolve_text_ref(ref, source, sections=structure)
    assert resolved.selector == SelectorStatus.resolved
    assert resolved.method == ResolutionMethod.section_anchors
    assert resolved.span is not None
    assert (resolved.span.start, resolved.span.end) == (design_start, later_start)

    stale_end = selector.model_copy(update={"end_anchor": HeadingAnchor(exact="## Missing")})
    mismatch = resolve_text_ref(
        ref.model_copy(update={"selector": stale_end}), source, sections=structure
    )
    assert mismatch.selector == SelectorStatus.boundary_mismatched
    assert mismatch.span is not None


def test_spanref_quote_construction_and_batch_resolution():
    source = "alpha target omega"
    ref = SpanRef.from_quote("target", source)
    assert ref.resolve(source) == (6, 12)
    assert ref.prefix is not None
    assert ref.suffix is not None

    refs = [ref, SpanRef(exact="absent"), SpanRef(exact="target")]
    assert resolve_batch(refs, source) == [(6, 12), None, (6, 12)]
