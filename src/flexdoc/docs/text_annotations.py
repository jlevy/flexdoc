"""Small consumer-owned annotation values targeted by portable TextRefs."""

from __future__ import annotations

from collections.abc import Sequence
from io import StringIO
from typing import Literal, Self

from frontmatter_format import new_yaml
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from flexdoc.docs.serialization import clean_yaml
from flexdoc.docs.text_ref import (
    TEXTREF_FORMAT,
    DocRef,
    Selector,
    SourceHash,
    TextRef,
)

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
    source_hash: SourceHash | None = None
    annotations: list[AnnotationSetEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_set(self) -> Self:
        ids = [annotation.id for annotation in self.annotations]
        if len(ids) != len(set(ids)):
            raise ValueError("annotation ids must be unique within a set")
        for annotation in self.annotations:
            TextRef(
                format=TEXTREF_FORMAT,
                document=self.document,
                source_hash=self.source_hash,
                selector=annotation.target,
            )
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
                    format=TEXTREF_FORMAT,
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
