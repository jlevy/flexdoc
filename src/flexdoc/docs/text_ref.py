"""Strict TextRef values, canonical source hashing, and the reversible URI codec."""

from __future__ import annotations

import hashlib
import re
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

TEXTREF_FORMAT = "textref/0.1"
"""Current normative JSON format identifier."""

TEXTREF_URI_PREFIX = "textref:0.1?"
"""Current reversible URI projection prefix."""

_MAX_JSON_SAFE_INTEGER = 9_007_199_254_740_991
"""Largest integer represented exactly by interoperable JSON number implementations."""

_MAX_TEXTREF_URI_LENGTH = 8_192
"""Conservative export and parser limit for portable TextRef URIs."""

_SOURCE_HASH_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
_PERCENT_ESCAPE_PATTERN = re.compile(r"%(?![0-9A-Fa-f]{2})")

Position = Annotated[int, Field(ge=0, le=_MAX_JSON_SAFE_INTEGER, strict=True)]


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
    """A non-empty arbitrary source range anchored by exact text and optional context."""

    type: Literal["span"]
    exact: str
    prefix: str | None = None
    suffix: str | None = None
    start: Position | None = None

    _exact = field_validator("exact")(_validate_required_string)
    _prefix = field_validator("prefix")(_validate_optional_string)
    _suffix = field_validator("suffix")(_validate_optional_string)


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


class TextRef(_StrictModel):
    """A document plus an optional source hash and optional typed selector."""

    format: Literal["textref/0.1"]
    document: DocRef
    source_hash: str | None = None
    selector: Selector | None = None
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("source_hash")
    @classmethod
    def _validate_source_hash(cls, value: str | None) -> str | None:
        if value is not None and _SOURCE_HASH_PATTERN.fullmatch(value) is None:
            raise ValueError("source_hash must be a lowercase algorithm-qualified SHA-256 digest")
        return value

    @field_validator("extensions")
    @classmethod
    def _validate_extensions(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        for key in value:
            owner, separator, name = key.partition(":")
            if not separator or not owner or not name:
                raise ValueError("extension keys must be namespaced as owner:name")
        return value

    @model_validator(mode="after")
    def _validate_context_free_point(self) -> Self:
        if isinstance(self.selector, PointSelector) and not (
            self.selector.prefix or self.selector.suffix
        ):
            if self.selector.position != 0 or self.source_hash is None:
                raise ValueError("a point without context requires position zero and a source hash")
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
    fields = [("type", "span"), ("exact", selector.exact)]
    if selector.prefix is not None:
        fields.append(("prefix", selector.prefix))
    if selector.suffix is not None:
        fields.append(("suffix", selector.suffix))
    if selector.start is not None:
        fields.append(("start", str(selector.start)))
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
        if exact is None:
            raise ValueError("span URI requires exact")
        return SpanSelector(
            type="span",
            exact=exact,
            prefix=values.pop("prefix", None),
            suffix=values.pop("suffix", None),
            start=_parse_position(values, "start"),
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
    "DocRef",
    "HeadingAnchor",
    "PointAffinity",
    "PointSelector",
    "SectionSelector",
    "SpanSelector",
    "TextRef",
    "TextRefTargetKind",
    "normalize_source",
    "source_hash",
]
