"""Document-bound construction and exact resolution of portable TextRefs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from flexdoc.docs.base_blocks import BaseBlock
from flexdoc.docs.block_tree import Block, walk_blocks
from flexdoc.docs.links import Link, LinkForm
from flexdoc.docs.node import Node, NodeKind
from flexdoc.docs.paragraphs import Paragraph, Sentence
from flexdoc.docs.sections import Section
from flexdoc.docs.span_ref import SpanRef
from flexdoc.docs.text_ref import (
    TEXTREF_FORMAT,
    DocRef,
    HeadingAnchor,
    PointAffinity,
    PointSelector,
    SectionRange,
    SectionSelector,
    SpanSelector,
    TextRef,
    TextRefResolution,
    resolve_text_ref,
    source_hash,
)

if TYPE_CHECKING:
    from flexdoc.docs.flex_doc import FlexDoc

_CONTEXT_CHARS = 24


class TextRefTargetError(ValueError):
    """A requested target cannot be grounded in the bound document snapshot."""


@dataclass(frozen=True)
class TextRefContext:
    """
    Bind a document locator to one FlexDoc source snapshot. TextRefs remain derived
    values; this context only caches the snapshot hash and adapts public source spans.
    """

    _doc: FlexDoc
    document: DocRef
    source_hash: str

    @classmethod
    def bind(cls, doc: FlexDoc, document: str | DocRef) -> TextRefContext:
        """Bind `document` to `doc` and compute its canonical source hash once."""
        locator = document if isinstance(document, DocRef) else DocRef(document)
        return cls(doc, locator, source_hash(doc.source_text))

    def whole_document(self) -> TextRef:
        """Reference the complete bound source snapshot."""
        return self._text_ref(None)

    def for_span(self, start: int, end: int) -> TextRef:
        """Reference one non-empty half-open source range."""
        self._validate_span(start, end)
        evidence = SpanRef.from_span(self._doc.source_text, start, end)
        return self._text_ref(
            SpanSelector(
                type="span",
                exact=evidence.exact,
                prefix=evidence.prefix,
                suffix=evidence.suffix,
                start=start,
            )
        )

    def for_point(
        self,
        position: int,
        *,
        affinity: PointAffinity | str = PointAffinity.after,
    ) -> TextRef:
        """Reference a zero-width source boundary with immediate recovery context."""
        source = self._doc.source_text
        if not 0 <= position <= len(source):
            raise TextRefTargetError("point is outside the bound document")
        prefix = source[max(0, position - _CONTEXT_CHARS) : position] or None
        suffix = source[position : position + _CONTEXT_CHARS] or None
        return self._text_ref(
            PointSelector(
                type="point",
                position=position,
                affinity=PointAffinity(affinity),
                prefix=prefix,
                suffix=suffix,
            )
        )

    def for_section(self, section: Section) -> TextRef:
        """Reference a complete heading-owned section using semantic anchors."""
        if section._doc is not self._doc:  # pyright: ignore[reportPrivateUsage]
            raise TextRefTargetError("section belongs to a different document")
        sections = self._flat_sections()
        matching_index = next(
            (index for index, candidate in enumerate(sections) if candidate.span == section.span),
            None,
        )
        if matching_index is None:
            raise TextRefTargetError("section does not match the bound document")
        current = sections[matching_index]
        boundary = next(
            (
                candidate
                for candidate in sections[matching_index + 1 :]
                if candidate.level <= current.level
            ),
            None,
        )
        return self._text_ref(
            SectionSelector(
                type="section",
                syntax="commonmark",
                start_anchor=self._heading_anchor(current),
                end_anchor=self._heading_anchor(boundary) if boundary is not None else None,
            )
        )

    def for_target(
        self,
        target: Paragraph | Sentence | Block | BaseBlock | Link | Node | Section | tuple[int, int],
    ) -> TextRef:
        """Map one supported public FlexDoc value to its portable source reference."""
        if isinstance(target, Section):
            return self.for_section(target)
        if isinstance(target, Node) and target.kind == NodeKind.section:
            if target.source_span is None:
                raise TextRefTargetError("target is not locatable")
            section = next(
                (
                    section
                    for section in self._flat_sections()
                    if section.span == target.source_span
                ),
                None,
            )
            if section is None or not self._owns_node(target):
                raise TextRefTargetError("target belongs to a different document")
            return self.for_section(section)

        span = self._target_span(target)
        self._validate_target(target, span)
        return self.for_span(*span)

    def resolve(self, text_ref: TextRef) -> TextRefResolution:
        """Resolve a TextRef exactly against the bound source and section structure."""
        return resolve_text_ref(
            text_ref,
            self._doc.source_text,
            document=self.document,
            sections=self._section_ranges(),
        )

    def _text_ref(self, selector: SpanSelector | PointSelector | SectionSelector | None) -> TextRef:
        return TextRef(
            format=TEXTREF_FORMAT,
            document=self.document,
            source_hash=self.source_hash,
            selector=selector,
        )

    def _target_span(
        self,
        target: Paragraph | Sentence | Block | BaseBlock | Link | Node | tuple[int, int],
    ) -> tuple[int, int]:
        if isinstance(target, tuple):
            if len(target) != 2:
                raise TextRefTargetError("explicit target must be a (start, end) integer pair")
            return target
        if isinstance(target, BaseBlock):
            return target.block.span
        if isinstance(target, (Paragraph, Sentence, Block)):
            return target.span
        if isinstance(target, Link):
            if target.span is None:
                raise TextRefTargetError("target is not locatable")
            return target.span
        if target.source_span is None:
            raise TextRefTargetError("target is not locatable")
        return target.source_span

    def _validate_target(
        self,
        target: Paragraph | Sentence | Block | BaseBlock | Link | Node | tuple[int, int],
        span: tuple[int, int],
    ) -> None:
        self._validate_span(*span)
        if isinstance(target, Paragraph):
            expected = target.original_text
            if self._doc.source_text[slice(*span)] != expected:
                raise TextRefTargetError("target does not match the bound document")
        elif isinstance(target, Sentence):
            expected = target.original_text if target.original_text is not None else target.text
            if self._doc.source_text[slice(*span)] != expected:
                raise TextRefTargetError("target does not match the bound document")
        elif isinstance(target, Block) and not self._owns_block(target):
            raise TextRefTargetError("target belongs to a different document")
        elif isinstance(target, BaseBlock) and not any(
            candidate == target for candidate in self._doc.base_blocks()
        ):
            raise TextRefTargetError("target belongs to a different document")
        elif isinstance(target, Link) and not any(
            link is target for link in self._doc.links(link_forms=set(LinkForm))
        ):
            raise TextRefTargetError("target belongs to a different document")
        elif isinstance(target, Node) and not self._owns_node(target):
            raise TextRefTargetError("target belongs to a different document")

    def _validate_span(self, start: int, end: int) -> None:
        if not 0 <= start < end <= len(self._doc.source_text):
            raise TextRefTargetError("span is empty or outside the bound document")

    def _owns_block(self, target: Block) -> bool:
        return any(block is target for block, _depth in walk_blocks(self._doc.blocks()))

    def _owns_node(self, target: Node) -> bool:
        return self._doc.node_table().nodes.get(target.id) is target

    def _flat_sections(self) -> list[Section]:
        sections: list[Section] = []

        def append_tree(values: list[Section]) -> None:
            for value in values:
                sections.append(value)
                append_tree(value.children)

        append_tree(self._doc.sections())
        sections.sort(key=lambda section: section.heading_block.span[0])
        return sections

    def _heading_anchor(self, section: Section) -> HeadingAnchor:
        start, end = section.heading_block.span
        evidence = SpanRef.from_span(self._doc.source_text, start, end)
        return HeadingAnchor(
            exact=evidence.exact,
            prefix=evidence.prefix,
            suffix=evidence.suffix,
            start=start,
        )

    def _section_ranges(self) -> tuple[SectionRange, ...]:
        sections = self._flat_sections()
        ranges: list[SectionRange] = []
        for index, section in enumerate(sections):
            boundary = next(
                (
                    candidate.heading_block.span[0]
                    for candidate in sections[index + 1 :]
                    if candidate.level <= section.level
                ),
                None,
            )
            ranges.append(
                SectionRange(
                    heading_start=section.heading_block.span[0],
                    heading_end=section.heading_block.span[1],
                    section_end=section.span[1],
                    boundary_start=boundary,
                )
            )
        return tuple(ranges)
