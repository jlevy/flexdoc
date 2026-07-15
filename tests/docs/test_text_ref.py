"""Behavioral contract for TextRef values and codecs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from flexdoc.docs.text_ref import (
    TEXTREF_FORMAT,
    DocRef,
    HeadingAnchor,
    PointAffinity,
    PointSelector,
    SectionSelector,
    SpanSelector,
    TextRef,
    TextRefTargetKind,
    normalize_source,
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
