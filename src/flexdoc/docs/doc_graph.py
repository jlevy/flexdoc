"""
Pydantic v2 schema for the DocGraph serialized projection and the builder
that derives it from a `FlexDoc`.

`DocGraph` is the language-neutral JSON contract described in flexdoc-spec section 10.
It is a derived, read-only snapshot: the Python core is `FlexDoc`; edits go through
`FlexDoc`/source and re-derive. Authored as Pydantic models (DR-3) that emit a
JSON Schema.

Pydantic validation and schema emission sit at the wire boundary, while the hot
in-memory parse model (`Node`, `Block`, and the editing view) stays in plain dataclasses
with no validation overhead.
"""

from __future__ import annotations

from collections.abc import Set as AbstractSet
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from flexdoc.docs.collect import INLINE_KINDS
from flexdoc.docs.node import Layer, Node, NodeKind, NodeTable
from flexdoc.docs.serialization import clean_yaml
from flexdoc.docs.text_annotations import AnnotationSet, AnnotationSetEntry
from flexdoc.docs.text_ref import DocRef, Position, SourceHash, normalize_source, source_hash


class Detail(StrEnum):
    """
    Payload sub-options controlling richness within enabled layers (DR-5, E9).
    These are not top-level layers but detail flags: `text` adds per-node source
    text, `inline` includes inline nodes, `tokens` and `coords` add those payloads.
    """

    text = "text"
    inline = "inline"
    tokens = "tokens"
    coords = "coords"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, strict=True)


class SourceInfo(_StrictModel):
    """Source metadata for the document backing a `DocGraph`."""

    format: Annotated[str, Field(min_length=1, strict=True)]
    offset_unit: Literal["unicode_code_points"] = "unicode_code_points"
    document: DocRef
    source_hash: SourceHash
    text: str | None = None

    @model_validator(mode="after")
    def _text_matches_hash(self) -> Self:
        if self.text is not None:
            if normalize_source(self.text) != self.text:
                raise ValueError("source text must use canonical LF line endings")
            if source_hash(self.text) != self.source_hash:
                raise ValueError("source text does not match source_hash")
        return self


class SourceSpan(_StrictModel):
    """A `[start, end)` span in Unicode code points."""

    start: Position
    end: Position

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.end < self.start:
            raise ValueError("source span end must not precede start")
        return self


class NodeModel(_StrictModel):
    """
    Serialization model for a single node. Mirrors the runtime `Node` dataclass
    with JSON-friendly field types. `source_span` is a `{start, end}` object
    (or null for unlocatable nodes like reference links).
    """

    id: str
    kind: str
    layer: str
    parent: str | None = None
    children: list[str] = Field(default_factory=list)
    source_span: SourceSpan | None = None
    # JSON's value space, validated at serialization: attrs are part of the frozen
    # cross-language DocGraph contract (see `flexdoc.docs.node.AttrValue`).
    attrs: dict[str, JsonValue] = Field(default_factory=dict)
    text: str | None = None


class Views(_StrictModel):
    """Derived view indexes: arrays of node ids for common projections."""

    toc: list[str] = Field(default_factory=list)
    blocks: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    paragraphs: list[str] = Field(default_factory=list)
    sentences: list[str] = Field(default_factory=list)


class DocGraph(_StrictModel):
    """
    The DocGraph serialized projection (flexdoc-spec section 10). A single,
    source-anchored JSON object from which any view (block tree, section tree,
    inline index) and any rollup is derivable.

    The `schema` JSON key carries the version string; in Python it is accessed
    as `schema_` (with `Field(alias="schema")`).

    `annotations` contains optional source-relative annotation entries. `layout` and
    `provenance` remain reserved for later phases (flexdoc-spec section 14).
    """

    schema_: Literal["DocGraph/v0.2"] = Field(default="DocGraph/v0.2", alias="schema")
    source: SourceInfo
    nodes: list[NodeModel]
    views: Views

    annotations: list[AnnotationSetEntry] = Field(default_factory=list)
    layout: list[object] = Field(default_factory=list)
    provenance: list[object] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_graph_references(self) -> Self:
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("DocGraph node ids must be unique")
        known_ids = set(node_ids)
        for node in self.nodes:
            referenced_ids = [*node.children]
            if node.parent is not None:
                referenced_ids.append(node.parent)
            if any(node_id not in known_ids for node_id in referenced_ids):
                raise ValueError(f"node {node.id} contains a dangling node reference")
            if self.source.text is not None and node.source_span is not None:
                if node.source_span.end > len(self.source.text):
                    raise ValueError(f"node {node.id} source span exceeds source text")
                if node.text is not None:
                    selected = self.source.text[node.source_span.start : node.source_span.end]
                    if node.text != selected:
                        raise ValueError(f"node {node.id} text does not match source span")
        for view_name in ("toc", "blocks", "links", "paragraphs", "sentences"):
            view_ids = getattr(self.views, view_name)
            if any(node_id not in known_ids for node_id in view_ids):
                raise ValueError(f"view {view_name} contains a dangling node reference")
        return self

    def to_yaml(self) -> str:
        """
        Serialize to clean, deterministic YAML: the same model as `model_dump_json`
        but in block style with `|` block scalars for multi-line text, field order
        preserved, and `None`/empty mappings and lists suppressed (so leaf nodes carry
        no `children: []` and reserved layers do not appear when empty). JSON stays the
        canonical wire form; YAML is the human/golden form (see `flexdoc.docs.debug`).
        """
        return clean_yaml(self.model_dump(by_alias=True))


# Default layers included when none are specified.
DEFAULT_INCLUDE: frozenset[Layer] = frozenset({Layer.markdown, Layer.document})


def build_doc_graph(
    table: NodeTable,
    *,
    document: str | DocRef,
    include: AbstractSet[Layer] = DEFAULT_INCLUDE,
    detail: AbstractSet[Detail] = frozenset(),  # pyright: ignore[reportCallInDefaultInitializer]
    annotations: AnnotationSet | None = None,
) -> DocGraph:
    """
    Build a `DocGraph` from a `NodeTable`.

    `include` selects which layers' nodes and views are serialized. Enabling
    `Layer.document` auto-enables `Layer.markdown` (its dependency). The
    structural core (ids, kinds, layer, parent/children, source_span) is
    always present for included layers.

    `document` supplies the consumer-owned locator shared by every graph span.
    `detail` controls payload richness: `Detail.text` adds per-node source
    text (and includes `source.text`); `Detail.inline` includes inline nodes;
    `Detail.tokens` and `Detail.coords` are reserved for future payloads.

    `annotations` optionally embeds source-relative annotation entries after verifying
    that their shared document and source hash identify this snapshot.
    """
    # Auto-enable markdown when document is included.
    layers = set(include)
    if Layer.document in layers:
        layers.add(Layer.markdown)
    enabled_layers = frozenset(layers)

    source_text = table.source_text

    include_inline = Detail.inline in detail
    include_text = Detail.text in detail

    # Build the node list, filtering by enabled layers (and inline detail).
    node_models: list[NodeModel] = []

    for nid, node in table.nodes.items():
        if node.layer not in enabled_layers:
            continue
        if node.kind in INLINE_KINDS and not include_inline:
            continue

        span_model: SourceSpan | None = None
        if node.source_span is not None:
            span_model = SourceSpan(start=node.source_span[0], end=node.source_span[1])

        node_text: str | None = None
        if include_text and node.source_span is not None:
            node_text = source_text[node.source_span[0] : node.source_span[1]]

        # Filter children to only those that are included.
        filtered_children = [
            cid
            for cid in node.children
            if _node_included(table.nodes[cid], enabled_layers, include_inline)
        ]

        node_models.append(
            NodeModel(
                id=nid,
                kind=node.kind.value,
                layer=node.layer.value,
                parent=node.parent
                if node.parent
                and _is_parent_included(node.parent, table.nodes, enabled_layers, include_inline)
                else None,
                children=filtered_children,
                source_span=span_model,
                attrs=node.attrs,
                text=node_text,
            )
        )

    # Build views from included nodes.
    toc_ids: list[str] = []
    block_ids: list[str] = []
    link_ids: list[str] = []
    paragraph_ids: list[str] = []
    sentence_ids: list[str] = []

    for nm in node_models:
        kind = nm.kind
        layer = nm.layer
        if kind == NodeKind.section.value and layer == Layer.document.value:
            toc_ids.append(nm.id)
        if layer == Layer.markdown.value and kind not in {k.value for k in INLINE_KINDS}:
            block_ids.append(nm.id)
        if kind == NodeKind.link.value:
            link_ids.append(nm.id)
        if kind == NodeKind.paragraph.value and layer == Layer.textual.value:
            paragraph_ids.append(nm.id)
        if kind == NodeKind.sentence.value and layer == Layer.textual.value:
            sentence_ids.append(nm.id)

    locator = document if isinstance(document, DocRef) else DocRef(document)
    actual_source_hash = source_hash(source_text)
    annotation_entries: list[AnnotationSetEntry] = []
    if annotations is not None:
        if annotations.document != locator:
            raise ValueError("annotation set document does not match the DocGraph document")
        if annotations.source_hash is None:
            raise ValueError("annotation set source hash is required for DocGraph embedding")
        if annotations.source_hash != actual_source_hash:
            raise ValueError("annotation set source hash does not match the document snapshot")
        annotation_entries = annotations.annotations

    source_info = SourceInfo(
        format="markdown",
        document=locator,
        source_hash=actual_source_hash,
        text=source_text if include_text else None,
    )

    views = Views(
        toc=toc_ids,
        blocks=block_ids,
        links=link_ids,
        paragraphs=paragraph_ids,
        sentences=sentence_ids,
    )

    return DocGraph(
        source=source_info,
        nodes=node_models,
        views=views,
        annotations=annotation_entries,
    )


def _node_included(
    node: Node,
    enabled_layers: frozenset[Layer],
    include_inline: bool,
) -> bool:
    """Check whether a node would be included given the current layer/detail settings."""
    if node.layer not in enabled_layers:
        return False
    if node.kind in INLINE_KINDS and not include_inline:
        return False
    return True


def _is_parent_included(
    parent_id: str,
    nodes: dict[str, Node],
    enabled_layers: frozenset[Layer],
    include_inline: bool,
) -> bool:
    """
    Check whether a parent node would itself be included, using the same predicate
    as child filtering so a node never points to a parent that was omitted.
    """
    parent = nodes.get(parent_id)
    if parent is None:
        return False
    return _node_included(parent, enabled_layers, include_inline)
