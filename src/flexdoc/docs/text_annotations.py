"""Small consumer-owned annotation values targeted by portable TextRefs."""

from __future__ import annotations

from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from io import StringIO
from typing import Literal, Self

from frontmatter_format import new_yaml
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from flexdoc.docs.doc_graph import (
    DEFAULT_INCLUDE,
    Detail,
    NodeModel,
    SourceInfo,
    Views,
    build_doc_graph,
    clean_yaml,
)
from flexdoc.docs.node import Layer, NodeTable
from flexdoc.docs.text_ref import DocRef, Selector, TextRef, source_hash

ANNOTATION_FORMAT = "text-annotations/0.1"


def _required(value: str) -> str:
    if not value:
        raise ValueError("value must not be empty")
    return value


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class TextBody(_StrictModel):
    """A discriminated plain-text annotation body."""

    type: Literal["text"]
    value: str

    _value = field_validator("value")(_required)


class _AnnotationFields(_StrictModel):
    id: str
    motivations: list[str] = Field(min_length=1)
    body: TextBody | None = None
    style: str | None = None
    tags: list[str] = Field(default_factory=list)
    captured_text: str | None = None
    provenance: dict[str, JsonValue] = Field(default_factory=dict)

    _id = field_validator("id")(_required)

    @field_validator("motivations", "tags")
    @classmethod
    def _nonempty_unique_strings(cls, values: list[str]) -> list[str]:
        if any(not value for value in values):
            raise ValueError("values must not be empty")
        if len(values) != len(set(values)):
            raise ValueError("values must be unique")
        return values

    @field_validator("style")
    @classmethod
    def _optional_nonempty(cls, value: str | None) -> str | None:
        if value == "":
            raise ValueError("value must not be empty")
        return value


class TextAnnotation(_AnnotationFields):
    """One independent annotation whose target is a complete TextRef."""

    target: TextRef


class AnnotationSetEntry(_AnnotationFields):
    """One annotation with a selector relative to its enclosing annotation set."""

    target: Selector | None = Field(discriminator="type")


class AnnotationSet(_StrictModel):
    """A concise one-document sidecar that hoists shared TextRef source identity."""

    format: Literal["text-annotations/0.1"]
    document: DocRef
    source_hash: str | None = None
    annotations: list[AnnotationSetEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_set(self) -> Self:
        if self.source_hash is not None:
            TextRef(
                format="textref/0.1",
                document=self.document,
                source_hash=self.source_hash,
            )
        ids = [annotation.id for annotation in self.annotations]
        if len(ids) != len(set(ids)):
            raise ValueError("annotation ids must be unique within a set")
        return self

    @classmethod
    def from_annotations(cls, annotations: Sequence[TextAnnotation]) -> AnnotationSet:
        """Hoist shared source identity from complete, same-document annotations."""
        if not annotations:
            raise ValueError("cannot infer one document from an empty annotation list")
        first = annotations[0].target
        if any(
            annotation.target.document != first.document
            or annotation.target.source_hash != first.source_hash
            for annotation in annotations
        ):
            raise ValueError("annotation set requires targets from one document snapshot")
        entries = [
            AnnotationSetEntry(
                **annotation.model_dump(exclude={"target"}),
                target=annotation.target.selector,
            )
            for annotation in annotations
        ]
        return cls(
            format=ANNOTATION_FORMAT,
            document=first.document,
            source_hash=first.source_hash,
            annotations=entries,
        )

    def expand(self) -> tuple[TextAnnotation, ...]:
        """Expand bare selectors into complete TextRef annotation targets."""
        return tuple(
            TextAnnotation(
                **annotation.model_dump(exclude={"target"}),
                target=TextRef(
                    format="textref/0.1",
                    document=self.document,
                    source_hash=self.source_hash,
                    selector=annotation.target,
                ),
            )
            for annotation in self.annotations
        )

    def to_yaml(self) -> str:
        """Serialize this strict sidecar as deterministic block-style YAML."""
        return clean_yaml(self.model_dump(mode="json"))

    @classmethod
    def from_yaml(cls, value: str) -> AnnotationSet:
        """Parse restricted safe YAML, then apply the same strict model validation."""
        yaml = new_yaml(typ="safe")
        loaded = yaml.load(StringIO(value))
        if not isinstance(loaded, dict):
            raise ValueError("annotation YAML must contain one mapping")
        return cls.model_validate(loaded)


class SourceInfoV2(SourceInfo):
    """DocGraph v0.2 source metadata that binds embedded bare selectors."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    document: DocRef
    source_hash: str

    @model_validator(mode="after")
    def _validate_source_hash(self) -> Self:
        TextRef(
            format="textref/0.1",
            document=self.document,
            source_hash=self.source_hash,
        )
        return self


class DocGraphV2(BaseModel):
    """Explicit annotation-bearing DocGraph projection; v0.1 remains unchanged."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["DocGraph/v0.2"] = Field(default="DocGraph/v0.2", alias="schema")
    source: SourceInfoV2
    nodes: list[NodeModel]
    views: Views
    annotations: list[AnnotationSetEntry]
    layout: list[object] = Field(default_factory=list)
    provenance: list[object] = Field(default_factory=list)

    def to_yaml(self) -> str:
        """Serialize the v0.2 projection using the deterministic DocGraph style."""
        return clean_yaml(self.model_dump(by_alias=True, mode="json"))


def build_doc_graph_v2(
    table: NodeTable,
    annotation_set: AnnotationSet,
    *,
    include: AbstractSet[Layer] = DEFAULT_INCLUDE,
    detail: AbstractSet[Detail] = frozenset(),  # pyright: ignore[reportCallInDefaultInitializer]
) -> DocGraphV2:
    """Build strict DocGraph/v0.2 with source-relative annotation selectors."""
    actual_hash = source_hash(table.source_text)
    if annotation_set.source_hash is None:
        raise ValueError("annotation set source hash is required for DocGraph/v0.2")
    if annotation_set.source_hash != actual_hash:
        raise ValueError("annotation set source hash does not match the document snapshot")
    base = build_doc_graph(table, include=include, detail=detail)
    source = SourceInfoV2(
        **base.source.model_dump(),
        document=annotation_set.document,
        source_hash=actual_hash,
    )
    return DocGraphV2(
        source=source,
        nodes=base.nodes,
        views=base.views,
        annotations=annotation_set.annotations,
    )
