"""Strict TextRef values, canonical source hashing, and the reversible URI codec."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Literal, Self
from urllib.parse import quote, unquote_to_bytes

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    RootModel,
    field_validator,
    model_validator,
)
from typing_extensions import override

from flexdoc.docs.span_ref import find_occurrences, resolve_quote_exact

TEXTREF_FORMAT = "textref/0.1"
"""Current normative JSON format identifier."""

TEXTREF_URI_PREFIX = "textref:0.1?"
"""Current reversible URI projection prefix."""

_MAX_JSON_SAFE_INTEGER = 9_007_199_254_740_991
"""Largest integer represented exactly by interoperable JSON number implementations."""

_MAX_TEXTREF_URI_LENGTH = 8_192
"""Conservative export and parser limit for portable TextRef URIs."""

_MIN_POINT_AFFINITY_CONTEXT = 8
"""Minimum owning context needed to recover a point after its other side changes."""

_SOURCE_HASH_REGEX = r"^sha256:[0-9a-f]{64}$"
_PERCENT_ESCAPE_PATTERN = re.compile(r"%(?![0-9A-Fa-f]{2})")

Position = Annotated[int, Field(ge=0, le=_MAX_JSON_SAFE_INTEGER, strict=True)]
"""A non-negative interoperable JSON integer used as a source offset."""

SourceHash = Annotated[str, Field(pattern=_SOURCE_HASH_REGEX, strict=True)]
"""An algorithm-qualified SHA-256 digest of canonical source text."""


def _validate_unicode(value: str) -> str:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("TextRef strings must contain only Unicode scalar values") from exc
    return value


def _validate_required_string(value: str) -> str:
    _validate_unicode(value)
    if not value:
        raise ValueError("value must not be empty")
    return value


def _validate_optional_string(value: str | None) -> str | None:
    if value is not None:
        _validate_required_string(value)
    return value


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DocRef(RootModel[str]):
    """A non-empty document locator. Parsing and serialization perform no I/O."""

    model_config = ConfigDict(frozen=True)

    @field_validator("root")
    @classmethod
    def _validate_root(cls, value: str) -> str:
        return _validate_required_string(value)

    @override
    def __str__(self) -> str:
        return self.root


class TextRefTargetKind(StrEnum):
    """The four target kinds represented by TextRef v0.1."""

    whole_document = "whole_document"
    span = "span"
    point = "point"
    section = "section"


class PointAffinity(StrEnum):
    """The side of a point that owns its identity across insertions."""

    before = "before"
    after = "after"


class DocumentStatus(StrEnum):
    """Whether the supplied document context can resolve the requested DocRef."""

    resolved = "resolved"
    unavailable = "unavailable"
    invalid = "invalid"


class SourceValidation(StrEnum):
    """Comparison of the optional expected source hash with supplied source."""

    absent = "absent"
    matched = "matched"
    mismatched = "mismatched"


class SelectorStatus(StrEnum):
    """Exact selector outcome, independent from document and source validation."""

    whole_document = "whole_document"
    resolved = "resolved"
    missing = "missing"
    ambiguous = "ambiguous"
    boundary_mismatched = "boundary_mismatched"
    unsupported = "unsupported"


class ResolutionMethod(StrEnum):
    """The exact evidence tier that produced a resolution."""

    source_position = "source_position"
    context_position = "context_position"
    exact_quote = "exact_quote"
    context_quote = "context_quote"
    point_context = "point_context"
    point_affinity = "point_affinity"
    section_structure = "section_structure"
    section_anchors = "section_anchors"
    none = "none"


class SourceRange(_StrictModel):
    """A resolved half-open range in canonical Unicode source."""

    start: Position
    end: Position

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.end < self.start:
            raise ValueError("source range end must not precede start")
        return self


class SectionRange(_StrictModel):
    """Structure-adapter evidence for one heading and its owned section."""

    heading_start: Position
    heading_end: Position
    section_end: Position
    boundary_start: Position | None = None

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if not self.heading_start < self.heading_end <= self.section_end:
            raise ValueError("section range must contain a non-empty heading")
        if self.boundary_start is not None and self.boundary_start < self.section_end:
            raise ValueError("section boundary must not precede section end")
        return self


class TextRefResolution(_StrictModel):
    """
    Typed exact-resolution result whose failure axes remain independent. Selector status
    is meaningful only when `document` is resolved.
    """

    document: DocumentStatus
    source_validation: SourceValidation
    selector: SelectorStatus
    method: ResolutionMethod = ResolutionMethod.none
    span: SourceRange | None = None
    candidates: tuple[SourceRange, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.selector in {SelectorStatus.whole_document, SelectorStatus.resolved}


@dataclass(frozen=True)
class _Selection:
    status: SelectorStatus
    method: ResolutionMethod = ResolutionMethod.none
    span: tuple[int, int] | None = None
    candidates: tuple[tuple[int, int], ...] = ()


class HeadingAnchor(_StrictModel):
    """Quote and position evidence for one complete CommonMark heading."""

    exact: str
    prefix: str | None = None
    suffix: str | None = None
    start: Position | None = None

    _exact = field_validator("exact")(_validate_required_string)
    _prefix = field_validator("prefix")(_validate_optional_string)
    _suffix = field_validator("suffix")(_validate_optional_string)


class SpanSelector(_StrictModel):
    """A non-empty source range with optional quote evidence or hash-bound positions."""

    type: Literal["span"]
    exact: str | None = None
    prefix: str | None = None
    suffix: str | None = None
    start: Position | None = None
    end: Position | None = None

    _exact = field_validator("exact")(_validate_optional_string)
    _prefix = field_validator("prefix")(_validate_optional_string)
    _suffix = field_validator("suffix")(_validate_optional_string)

    @model_validator(mode="after")
    def _has_complete_evidence(self) -> Self:
        if self.exact is None:
            if self.start is None or self.end is None:
                raise ValueError("span selector without exact requires start and end")
            if self.end <= self.start:
                raise ValueError("span selector must identify a non-empty range")
            if self.prefix is not None or self.suffix is not None:
                raise ValueError("span selector without exact does not use quote context")
        elif self.end is not None:
            if self.start is None or self.end != self.start + len(self.exact):
                raise ValueError("span end must equal start plus exact length")
        return self


class PointSelector(_StrictModel):
    """A zero-width source boundary with affinity and recovery context."""

    type: Literal["point"]
    position: Position | None = None
    affinity: PointAffinity
    prefix: str | None = None
    suffix: str | None = None

    _prefix = field_validator("prefix")(_validate_optional_string)
    _suffix = field_validator("suffix")(_validate_optional_string)

    @model_validator(mode="after")
    def _has_evidence(self) -> Self:
        if self.position is None and self.prefix is None and self.suffix is None:
            raise ValueError("point selector requires a position or context")
        return self


class SectionSelector(_StrictModel):
    """A complete CommonMark heading section, including nested subsections."""

    type: Literal["section"]
    syntax: Literal["commonmark"]
    start_anchor: HeadingAnchor
    end_anchor: HeadingAnchor | None = None


Selector = Annotated[
    SpanSelector | PointSelector | SectionSelector,
    Field(discriminator="type"),
]
"""The strict discriminated union of TextRef selector kinds."""


class TextRef(_StrictModel):
    """A document plus an optional source hash and optional typed selector."""

    format: Literal["textref/0.1"]
    document: DocRef
    source_hash: SourceHash | None = None
    selector: Selector | None = None
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("extensions")
    @classmethod
    def _validate_extensions(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        for key in value:
            owner, separator, name = key.partition(":")
            if not separator or not owner or not name:
                raise ValueError("extension keys must be namespaced as owner:name")
        return value

    @model_validator(mode="after")
    def _validate_evidence_requirements(self) -> Self:
        if isinstance(self.selector, PointSelector) and not (
            self.selector.prefix or self.selector.suffix
        ):
            if self.selector.position != 0 or self.source_hash is None:
                raise ValueError("a point without context requires position zero and a source hash")
        if isinstance(self.selector, SpanSelector) and self.selector.exact is None:
            if self.source_hash is None:
                raise ValueError("a span without exact requires a source hash")
        return self

    @property
    def target_kind(self) -> TextRefTargetKind:
        if self.selector is None:
            return TextRefTargetKind.whole_document
        return TextRefTargetKind(self.selector.type)

    def to_uri(self) -> str:
        """Return the canonical reversible `textref:0.1` URI projection."""
        if self.extensions:
            raise ValueError("TextRef extensions are not representable in v0.1 URIs")
        fields = [("doc", str(self.document))]
        if self.source_hash is not None:
            fields.append(("hash", self.source_hash))
        selector = self.selector
        if isinstance(selector, SpanSelector):
            fields.extend(_span_uri_fields(selector))
        elif isinstance(selector, PointSelector):
            fields.extend(_point_uri_fields(selector))
        elif isinstance(selector, SectionSelector):
            fields.extend(_section_uri_fields(selector))
        uri = TEXTREF_URI_PREFIX + "&".join(
            f"{_uri_encode(key)}={_uri_encode(value)}" for key, value in fields
        )
        if len(uri) > _MAX_TEXTREF_URI_LENGTH:
            raise ValueError("TextRef URI exceeds the v0.1 length limit")
        return uri

    @classmethod
    def from_uri(cls, uri: str) -> TextRef:
        """Parse a `textref:0.1` URI without resolving its document."""
        if len(uri) > _MAX_TEXTREF_URI_LENGTH:
            raise ValueError("TextRef URI exceeds the v0.1 length limit")
        if not uri.startswith(TEXTREF_URI_PREFIX):
            raise ValueError("unsupported TextRef URI version")
        if "+" in uri:
            raise ValueError("TextRef URIs encode spaces as %20, never +")
        values = _parse_query(uri.removeprefix(TEXTREF_URI_PREFIX))
        document = values.pop("doc", None)
        if document is None:
            raise ValueError("TextRef URI requires doc")
        digest = values.pop("hash", None)
        selector_type = values.pop("type", None)
        selector = _selector_from_uri(selector_type, values)
        if values:
            raise ValueError(f"unknown or incompatible TextRef URI fields: {sorted(values)}")
        return cls(
            format=TEXTREF_FORMAT,
            document=DocRef(document),
            source_hash=digest,
            selector=selector,
        )


def normalize_source(source: str) -> str:
    """Apply the TextRef v0.1 canonical source profile."""
    _validate_unicode(source)
    return source.replace("\r\n", "\n").replace("\r", "\n")


def source_hash(source: str) -> str:
    """Hash canonical UTF-8 source with an algorithm-qualified digest."""
    normalized = normalize_source(source)
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def resolve_text_ref(
    text_ref: TextRef,
    source: str,
    *,
    document: DocRef | None = None,
    sections: Sequence[SectionRange] | None = None,
) -> TextRefResolution:
    """
    Resolve one TextRef against supplied source and optional CommonMark structure.
    Document acquisition remains consumer-owned; `document` only verifies that the
    supplied snapshot belongs to the requested DocRef.
    """
    canonical_source = normalize_source(source)
    return _resolve_text_ref_normalized(
        text_ref,
        canonical_source,
        document=document,
        sections=sections,
    )


def _resolve_text_ref_normalized(
    text_ref: TextRef,
    source: str,
    *,
    document: DocRef | None = None,
    sections: Sequence[SectionRange] | None = None,
    actual_source_hash: str | None = None,
) -> TextRefResolution:
    """Resolve against canonical source, optionally reusing its trusted cached hash."""
    validation = _source_validation(text_ref, source, actual_source_hash)
    if document is not None and document != text_ref.document:
        return TextRefResolution(
            document=DocumentStatus.invalid,
            source_validation=validation,
            selector=SelectorStatus.unsupported,
        )

    selector = text_ref.selector
    if selector is None:
        return TextRefResolution(
            document=DocumentStatus.resolved,
            source_validation=validation,
            selector=SelectorStatus.whole_document,
            span=SourceRange(start=0, end=len(source)),
        )

    hash_matched = validation == SourceValidation.matched
    if isinstance(selector, SpanSelector):
        selected = _resolve_span(selector, source, hash_matched)
    elif isinstance(selector, PointSelector):
        selected = _resolve_point(selector, source, hash_matched)
    else:
        selected = _resolve_section(selector, source, hash_matched, sections)
    return _resolution_from_selection(selected, validation)


def _source_validation(
    text_ref: TextRef,
    source: str,
    actual_source_hash: str | None = None,
) -> SourceValidation:
    if text_ref.source_hash is None:
        return SourceValidation.absent
    digest = actual_source_hash if actual_source_hash is not None else source_hash(source)
    if text_ref.source_hash == digest:
        return SourceValidation.matched
    return SourceValidation.mismatched


def _resolution_from_selection(
    selection: _Selection, validation: SourceValidation
) -> TextRefResolution:
    span = SourceRange(start=selection.span[0], end=selection.span[1]) if selection.span else None
    candidates = tuple(SourceRange(start=start, end=end) for start, end in selection.candidates)
    return TextRefResolution(
        document=DocumentStatus.resolved,
        source_validation=validation,
        selector=selection.status,
        method=selection.method,
        span=span,
        candidates=candidates,
    )


def _resolve_quote(
    exact: str,
    prefix: str | None,
    suffix: str | None,
    start: int | None,
    source: str,
    hash_matched: bool,
) -> _Selection:
    result = resolve_quote_exact(
        exact,
        source,
        prefix=prefix,
        suffix=suffix,
        start=start,
        trust_position=hash_matched,
    )
    return _Selection(
        status=SelectorStatus(result.status),
        method=ResolutionMethod(result.method),
        span=result.span,
        candidates=result.candidates,
    )


def _resolve_span(selector: SpanSelector, source: str, hash_matched: bool) -> _Selection:
    if selector.exact is not None:
        return _resolve_quote(
            selector.exact,
            selector.prefix,
            selector.suffix,
            selector.start,
            source,
            hash_matched,
        )
    if (
        hash_matched
        and selector.start is not None
        and selector.end is not None
        and selector.end <= len(source)
    ):
        return _Selection(
            SelectorStatus.resolved,
            ResolutionMethod.source_position,
            (selector.start, selector.end),
        )
    return _Selection(SelectorStatus.missing)


def _context_matches(
    source: str,
    start: int,
    end: int,
    prefix: str | None,
    suffix: str | None,
) -> bool:
    if prefix is not None and source[max(0, start - len(prefix)) : start] != prefix:
        return False
    if suffix is not None and source[end : end + len(suffix)] != suffix:
        return False
    return True


def _resolve_point(selector: PointSelector, source: str, hash_matched: bool) -> _Selection:
    position = selector.position
    if position is not None and 0 <= position <= len(source):
        if hash_matched:
            return _Selection(
                SelectorStatus.resolved,
                ResolutionMethod.source_position,
                (position, position),
            )
        if (selector.prefix is not None or selector.suffix is not None) and _point_context_matches(
            selector, source, position
        ):
            return _Selection(
                SelectorStatus.resolved,
                ResolutionMethod.context_position,
                (position, position),
            )

    if selector.prefix is not None and selector.suffix is not None:
        boundaries = tuple(
            start + len(selector.prefix)
            for start in find_occurrences(source, selector.prefix + selector.suffix)
        )
        if len(boundaries) == 1:
            boundary = boundaries[0]
            return _Selection(
                SelectorStatus.resolved,
                ResolutionMethod.point_context,
                (boundary, boundary),
            )
        if len(boundaries) > 1:
            return _Selection(
                SelectorStatus.ambiguous,
                candidates=tuple((boundary, boundary) for boundary in boundaries),
            )

    owned_boundaries = _affinity_boundaries(selector, source)
    if len(owned_boundaries) == 1:
        boundary = owned_boundaries[0]
        return _Selection(
            SelectorStatus.resolved,
            ResolutionMethod.point_affinity,
            (boundary, boundary),
        )
    if len(owned_boundaries) > 1:
        return _Selection(
            SelectorStatus.ambiguous,
            candidates=tuple((boundary, boundary) for boundary in owned_boundaries),
        )
    return _Selection(SelectorStatus.missing)


def _point_context_matches(selector: PointSelector, source: str, position: int) -> bool:
    return _context_matches(
        source,
        position,
        position,
        selector.prefix,
        selector.suffix,
    )


def _affinity_boundaries(selector: PointSelector, source: str) -> tuple[int, ...]:
    if selector.affinity == PointAffinity.before:
        owned = selector.prefix
        if owned is None or len(owned) < _MIN_POINT_AFFINITY_CONTEXT:
            return ()
        return tuple(position + len(owned) for position in find_occurrences(source, owned))
    owned = selector.suffix
    if owned is None or len(owned) < _MIN_POINT_AFFINITY_CONTEXT:
        return ()
    return tuple(find_occurrences(source, owned))


def _resolve_section(
    selector: SectionSelector,
    source: str,
    hash_matched: bool,
    sections: Sequence[SectionRange] | None,
) -> _Selection:
    if sections is None:
        return _Selection(SelectorStatus.unsupported)
    start = selector.start_anchor
    start_result = _resolve_quote(
        start.exact,
        start.prefix,
        start.suffix,
        start.start,
        source,
        hash_matched,
    )
    if start_result.status == SelectorStatus.missing:
        return start_result
    heading_candidates = (
        (start_result.span,) if start_result.span is not None else start_result.candidates
    )
    structural = [
        section
        for section in sections
        if (section.heading_start, section.heading_end) in heading_candidates
    ]
    if not structural:
        return _Selection(SelectorStatus.missing)

    end_result: _Selection | None = None
    if selector.end_anchor is not None:
        end = selector.end_anchor
        end_result = _resolve_quote(
            end.exact,
            end.prefix,
            end.suffix,
            end.start,
            source,
            hash_matched,
        )
        if end_result.span is not None and len(structural) > 1:
            structural = [
                section
                for section in structural
                if (
                    section.boundary_start
                    if section.boundary_start is not None
                    else section.section_end
                )
                == end_result.span[0]
            ]

    if len(structural) > 1:
        return _Selection(
            SelectorStatus.ambiguous,
            candidates=tuple(
                (section.heading_start, section.section_end) for section in structural
            ),
        )
    if not structural:
        return _Selection(SelectorStatus.boundary_mismatched)

    section = structural[0]
    span = (section.heading_start, section.section_end)
    if end_result is None:
        return _Selection(
            SelectorStatus.resolved,
            ResolutionMethod.section_structure,
            span,
        )
    boundary = section.boundary_start if section.boundary_start is not None else section.section_end
    if end_result.span is None or end_result.span[0] != boundary:
        return _Selection(
            SelectorStatus.boundary_mismatched,
            ResolutionMethod.section_structure,
            span,
        )
    return _Selection(
        SelectorStatus.resolved,
        ResolutionMethod.section_anchors,
        span,
    )


def _uri_encode(value: str) -> str:
    return quote(value, safe="-._~")


def _uri_decode(value: str) -> str:
    if _PERCENT_ESCAPE_PATTERN.search(value):
        raise ValueError("invalid percent escape in TextRef URI")
    try:
        return unquote_to_bytes(value).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("TextRef URI values must be UTF-8") from exc


def _parse_query(query: str) -> dict[str, str]:
    if not query:
        raise ValueError("TextRef URI query must not be empty")
    values: dict[str, str] = {}
    for part in query.split("&"):
        if part.count("=") != 1:
            raise ValueError("TextRef URI parameters require one value")
        raw_key, raw_value = part.split("=", 1)
        key = _uri_decode(raw_key)
        value = _uri_decode(raw_value)
        if not key or not value:
            raise ValueError("TextRef URI parameters must not be empty")
        if key in values:
            raise ValueError(f"duplicate TextRef URI field: {key}")
        values[key] = value
    return values


def _span_uri_fields(selector: SpanSelector) -> list[tuple[str, str]]:
    fields = [("type", "span")]
    if selector.exact is not None:
        fields.append(("exact", selector.exact))
    if selector.prefix is not None:
        fields.append(("prefix", selector.prefix))
    if selector.suffix is not None:
        fields.append(("suffix", selector.suffix))
    if selector.start is not None:
        fields.append(("start", str(selector.start)))
    if selector.end is not None:
        fields.append(("end", str(selector.end)))
    return fields


def _point_uri_fields(selector: PointSelector) -> list[tuple[str, str]]:
    fields = [("type", "point")]
    if selector.prefix is not None:
        fields.append(("prefix", selector.prefix))
    if selector.suffix is not None:
        fields.append(("suffix", selector.suffix))
    if selector.position is not None:
        fields.append(("position", str(selector.position)))
    fields.append(("affinity", selector.affinity.value))
    return fields


def _anchor_uri_fields(prefix: str, anchor: HeadingAnchor) -> list[tuple[str, str]]:
    fields = [(f"{prefix}_exact", anchor.exact)]
    if anchor.prefix is not None:
        fields.append((f"{prefix}_prefix", anchor.prefix))
    if anchor.suffix is not None:
        fields.append((f"{prefix}_suffix", anchor.suffix))
    if anchor.start is not None:
        fields.append((f"{prefix}_pos", str(anchor.start)))
    return fields


def _section_uri_fields(selector: SectionSelector) -> list[tuple[str, str]]:
    fields = [("type", "section"), ("syntax", selector.syntax)]
    fields.extend(_anchor_uri_fields("start", selector.start_anchor))
    if selector.end_anchor is not None:
        fields.extend(_anchor_uri_fields("end", selector.end_anchor))
    return fields


def _parse_position(values: dict[str, str], key: str) -> int | None:
    raw = values.pop(key, None)
    if raw is None:
        return None
    if not raw.isascii() or not raw.isdecimal():
        raise ValueError(f"{key} must be a non-negative decimal integer")
    if len(raw) > 1 and raw.startswith("0"):
        raise ValueError(f"{key} must use canonical decimal form")
    return int(raw)


def _anchor_from_uri(values: dict[str, str], prefix: str) -> HeadingAnchor | None:
    exact = values.pop(f"{prefix}_exact", None)
    anchor_prefix = values.pop(f"{prefix}_prefix", None)
    anchor_suffix = values.pop(f"{prefix}_suffix", None)
    anchor_start = _parse_position(values, f"{prefix}_pos")
    if exact is None:
        if anchor_prefix is not None or anchor_suffix is not None or anchor_start is not None:
            raise ValueError(f"{prefix}_exact is required with {prefix} anchor fields")
        return None
    return HeadingAnchor(
        exact=exact,
        prefix=anchor_prefix,
        suffix=anchor_suffix,
        start=anchor_start,
    )


def _selector_from_uri(selector_type: str | None, values: dict[str, str]) -> Selector | None:
    if selector_type is None:
        return None
    if selector_type == "span":
        exact = values.pop("exact", None)
        return SpanSelector(
            type="span",
            exact=exact,
            prefix=values.pop("prefix", None),
            suffix=values.pop("suffix", None),
            start=_parse_position(values, "start"),
            end=_parse_position(values, "end"),
        )
    if selector_type == "point":
        affinity = values.pop("affinity", None)
        if affinity is None:
            raise ValueError("point URI requires affinity")
        return PointSelector(
            type="point",
            prefix=values.pop("prefix", None),
            suffix=values.pop("suffix", None),
            position=_parse_position(values, "position"),
            affinity=PointAffinity(affinity),
        )
    if selector_type == "section":
        syntax = values.pop("syntax", None)
        if syntax is None:
            raise ValueError("section URI requires syntax")
        if syntax != "commonmark":
            raise ValueError(f"unsupported section syntax: {syntax}")
        start_anchor = _anchor_from_uri(values, "start")
        if start_anchor is None:
            raise ValueError("section URI requires start anchor")
        return SectionSelector(
            type="section",
            syntax="commonmark",
            start_anchor=start_anchor,
            end_anchor=_anchor_from_uri(values, "end"),
        )
    raise ValueError(f"unsupported TextRef selector type: {selector_type}")


__all__ = [
    "TEXTREF_FORMAT",
    "TEXTREF_URI_PREFIX",
    "DocRef",
    "DocumentStatus",
    "HeadingAnchor",
    "PointAffinity",
    "PointSelector",
    "Position",
    "ResolutionMethod",
    "SectionRange",
    "SectionSelector",
    "Selector",
    "SelectorStatus",
    "SourceRange",
    "SourceValidation",
    "SpanSelector",
    "TextRef",
    "TextRefResolution",
    "TextRefTargetKind",
    "normalize_source",
    "resolve_text_ref",
    "source_hash",
]
