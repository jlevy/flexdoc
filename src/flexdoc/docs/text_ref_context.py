"""Document-bound construction and exact resolution of portable TextRefs."""

from __future__ import annotations

import json
from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property
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
    DocumentStatus,
    HeadingAnchor,
    PointAffinity,
    PointSelector,
    SectionRange,
    SectionSelector,
    SpanSelector,
    TextRef,
    TextRefResolution,
    _resolve_text_ref_normalized,
    source_hash,
)

if TYPE_CHECKING:
    from flexdoc.docs.flex_doc import FlexDoc
    from flexdoc.docs.text_annotations import AnnotationSet, TextAnnotation

_CONTEXT_CHARS = 24


class TextRefTargetError(ValueError):
    """A requested target cannot be grounded in the bound document snapshot."""


@dataclass(frozen=True)
class SourceCoordinate:
    """Derived one-based line and Unicode code-point column for a source offset."""

    offset: int
    line: int
    column: int


@dataclass(frozen=True)
class SourceLine:
    """One source line without its trailing newline."""

    number: int
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class TextRefSourceContext:
    """Exact resolution plus a bounded, derived source presentation window."""

    reference: TextRef
    resolution: TextRefResolution
    resolved_span: tuple[int, int] | None
    selected_source: str | None
    start: SourceCoordinate | None
    end: SourceCoordinate | None
    lines: tuple[SourceLine, ...] = ()
    omitted_before: bool = False
    omitted_after: bool = False


@dataclass
class _RenderWindow:
    start_line: int
    end_line: int
    lines: dict[int, SourceLine]
    annotations: list[tuple[TextAnnotation, TextRefSourceContext]]


@dataclass(frozen=True, eq=False)
class TextRefContext:
    """
    Bind a document locator to one FlexDoc source snapshot. TextRefs remain derived
    values; this context caches immutable snapshot indexes, adapts public source spans,
    and applies the caller's exact-quote size policy.
    """

    _doc: FlexDoc
    document: DocRef
    source_hash: str
    max_exact_chars: int | None = None

    @classmethod
    def bind(
        cls,
        doc: FlexDoc,
        document: str | DocRef,
        *,
        max_exact_chars: int | None = None,
    ) -> TextRefContext:
        """Bind `document` to `doc` and compute its canonical source hash once."""
        if max_exact_chars is not None and max_exact_chars < 0:
            raise ValueError("max_exact_chars must be non-negative")
        locator = document if isinstance(document, DocRef) else DocRef(document)
        return cls(doc, locator, source_hash(doc.source_text), max_exact_chars)

    def whole_document(self) -> TextRef:
        """Reference the complete bound source snapshot."""
        return self._text_ref(None)

    def for_span(
        self,
        start: int,
        end: int,
        *,
        include_exact: bool | None = None,
    ) -> TextRef:
        """
        Reference one non-empty half-open source range. `include_exact` overrides the
        context's `max_exact_chars` policy for this span.
        """
        self._validate_span(start, end)
        if include_exact is None:
            include_exact = self.max_exact_chars is None or end - start <= self.max_exact_chars
        if include_exact:
            evidence = SpanRef.from_span(self._doc.source_text, start, end)
            selector = SpanSelector(
                type="span",
                exact=evidence.exact,
                prefix=evidence.prefix,
                suffix=evidence.suffix,
                start=start,
            )
        else:
            selector = SpanSelector(type="span", start=start, end=end)
        return self._text_ref(selector)

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
        sections = self._flat_sections_cache
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
        *,
        include_exact: bool | None = None,
    ) -> TextRef:
        """
        Map one supported public FlexDoc value to its portable source reference.
        `include_exact` applies when the value maps to a span.
        """
        if isinstance(target, Section):
            return self.for_section(target)
        if isinstance(target, Node) and target.kind == NodeKind.section:
            if target.source_span is None:
                raise TextRefTargetError("target is not locatable")
            section = next(
                (
                    section
                    for section in self._flat_sections_cache
                    if section.span == target.source_span
                ),
                None,
            )
            if section is None or not self._owns_node(target):
                raise TextRefTargetError("target belongs to a different document")
            return self.for_section(section)

        span = self._target_span(target)
        self._validate_target(target, span)
        return self.for_span(*span, include_exact=include_exact)

    def resolve(self, text_ref: TextRef) -> TextRefResolution:
        """Resolve a TextRef exactly against the bound source and section structure."""
        return _resolve_text_ref_normalized(
            text_ref,
            self._doc.source_text,
            document=self.document,
            sections=self._section_ranges_cache,
            actual_source_hash=self.source_hash,
        )

    def context(
        self,
        text_ref: TextRef,
        *,
        before_lines: int = 2,
        after_lines: int = 2,
    ) -> TextRefSourceContext:
        """
        Resolve a TextRef and derive a bounded line window. Coordinates are
        one-based Unicode code-point labels and never become selector evidence.
        """
        if before_lines < 0:
            raise ValueError("before_lines must be non-negative")
        if after_lines < 0:
            raise ValueError("after_lines must be non-negative")
        resolution = self.resolve(text_ref)
        if resolution.span is None:
            return TextRefSourceContext(
                reference=text_ref,
                resolution=resolution,
                resolved_span=None,
                selected_source=None,
                start=None,
                end=None,
            )

        span = (resolution.span.start, resolution.span.end)
        source = self._doc.source_text
        source_lines = self._source_lines_cache
        start_index = _line_index(self._line_starts_cache, span[0])
        selected_end = span[0] if span[0] == span[1] else span[1] - 1
        end_index = _line_index(self._line_starts_cache, selected_end)
        window_start = max(0, start_index - before_lines)
        window_end = min(len(source_lines) - 1, end_index + after_lines)
        return TextRefSourceContext(
            reference=text_ref,
            resolution=resolution,
            resolved_span=span,
            selected_source=source[slice(*span)],
            start=_coordinate(source_lines, self._line_starts_cache, span[0]),
            end=_coordinate(source_lines, self._line_starts_cache, span[1]),
            lines=tuple(source_lines[window_start : window_end + 1]),
            omitted_before=window_start > 0,
            omitted_after=window_end < len(source_lines) - 1,
        )

    def render_context(
        self,
        text_ref: TextRef,
        *,
        before_lines: int = 2,
        after_lines: int = 2,
        max_quote_chars: int = 320,
        max_source_lines: int = 80,
    ) -> str:
        """Render one TextRef as compact deterministic Markdown-compatible context."""
        _validate_render_limits(max_quote_chars, max_source_lines)
        context = self.context(
            text_ref,
            before_lines=before_lines,
            after_lines=after_lines,
        )
        result = [
            "# TextRef",
            "",
            f"Document: {_json(str(text_ref.document))}",
            f"Target: {text_ref.target_kind.value}",
            f"URI: {_render_uri(text_ref)}",
            f"Resolution: {_resolution_label(context.resolution)}",
            f"Source validation: {context.resolution.source_validation.value}",
        ]
        location = _location_label(context)
        if location is not None:
            result.append(f"Range: {location}")
        if context.selected_source is not None:
            result.extend(_target_evidence_lines(text_ref, context, max_quote_chars))
        if context.lines:
            result.extend(["", "## Source", ""])
            result.extend(
                _render_source_lines(
                    context.lines,
                    omitted_before=context.omitted_before,
                    omitted_after=context.omitted_after,
                    max_source_lines=max_source_lines,
                )
            )
        return "\n".join(result) + "\n"

    def render_annotations(
        self,
        annotations: AnnotationSet | Sequence[TextAnnotation],
        *,
        before_lines: int = 2,
        after_lines: int = 2,
        max_quote_chars: int = 320,
        max_source_lines: int = 80,
    ) -> str:
        """
        Render consumer-owned annotations beside merged source windows. Unresolved
        and cross-document targets are grouped explicitly and retain their TextRefs.
        """
        from flexdoc.docs.text_annotations import AnnotationSet

        _validate_render_limits(max_quote_chars, max_source_lines)
        values = (
            annotations.expand() if isinstance(annotations, AnnotationSet) else tuple(annotations)
        )
        records = [
            (
                annotation,
                self.context(
                    annotation.target,
                    before_lines=before_lines,
                    after_lines=after_lines,
                ),
            )
            for annotation in values
        ]
        resolved = [record for record in records if record[1].resolution.resolved]
        unresolved = [record for record in records if not record[1].resolution.resolved]
        result = [
            "# TextRef annotations",
            "",
            f"Document: {_json(str(self.document))}",
            f"Annotations: {len(records)}",
        ]
        total_lines = len(self._source_lines_cache)
        for window in _merge_windows(resolved):
            heading = (
                f"Line {window.start_line}"
                if window.start_line == window.end_line
                else f"Lines {window.start_line}-{window.end_line}"
            )
            result.extend(["", f"## {heading}", ""])
            ordered_lines = tuple(window.lines[number] for number in sorted(window.lines))
            result.extend(
                _render_source_lines(
                    ordered_lines,
                    omitted_before=window.start_line > 1,
                    omitted_after=window.end_line < total_lines,
                    max_source_lines=max_source_lines,
                )
            )
            result.extend(["", "Annotations:"])
            for annotation, context in sorted(
                window.annotations,
                key=lambda record: (
                    record[1].resolved_span or (0, 0),
                    record[0].id,
                ),
            ):
                result.extend(_annotation_lines(annotation, context, max_quote_chars))

        grouped = _group_unresolved(unresolved)
        for heading in (
            "Missing",
            "Ambiguous",
            "Boundary mismatched",
            "Unsupported",
            "Orphaned",
        ):
            group = grouped.get(heading, [])
            if not group:
                continue
            result.extend(["", f"## {heading}"])
            for annotation, context in sorted(group, key=lambda record: record[0].id):
                result.extend(_annotation_lines(annotation, context, max_quote_chars))
        return "\n".join(result) + "\n"

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

    @cached_property
    def _source_lines_cache(self) -> tuple[SourceLine, ...]:
        return tuple(_source_lines(self._doc.source_text))

    @cached_property
    def _line_starts_cache(self) -> tuple[int, ...]:
        return tuple(line.start for line in self._source_lines_cache)

    @cached_property
    def _flat_sections_cache(self) -> tuple[Section, ...]:
        sections: list[Section] = []

        def append_tree(values: list[Section]) -> None:
            for value in values:
                sections.append(value)
                append_tree(value.children)

        append_tree(self._doc.sections())
        sections.sort(key=lambda section: section.heading_block.span[0])
        return tuple(sections)

    def _heading_anchor(self, section: Section) -> HeadingAnchor:
        start, end = section.heading_block.span
        evidence = SpanRef.from_span(self._doc.source_text, start, end)
        return HeadingAnchor(
            exact=evidence.exact,
            prefix=evidence.prefix,
            suffix=evidence.suffix,
            start=start,
        )

    @cached_property
    def _section_ranges_cache(self) -> tuple[SectionRange, ...]:
        sections = self._flat_sections_cache
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


def _source_lines(source: str) -> list[SourceLine]:
    lines: list[SourceLine] = []
    start = 0
    for number, text in enumerate(source.split("\n"), start=1):
        end = start + len(text)
        lines.append(SourceLine(number=number, start=start, end=end, text=text))
        start = end + 1
    return lines


def _line_index(line_starts: Sequence[int], offset: int) -> int:
    return max(0, bisect_right(line_starts, offset) - 1)


def _coordinate(
    lines: Sequence[SourceLine],
    line_starts: Sequence[int],
    offset: int,
) -> SourceCoordinate:
    line = lines[_line_index(line_starts, offset)]
    return SourceCoordinate(
        offset=offset,
        line=line.number,
        column=offset - line.start + 1,
    )


def _validate_render_limits(max_quote_chars: int, max_source_lines: int) -> None:
    if max_quote_chars < 32:
        raise ValueError("max_quote_chars must be at least 32")
    if max_source_lines < 3:
        raise ValueError("max_source_lines must be at least 3")


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _render_uri(text_ref: TextRef) -> str:
    try:
        return text_ref.to_uri()
    except ValueError:
        return "unavailable (use structured TextRef)"


def _resolution_label(resolution: TextRefResolution) -> str:
    if resolution.document != DocumentStatus.resolved:
        return f"document {resolution.document.value}"
    if resolution.method.value == "none":
        return resolution.selector.value
    return f"{resolution.selector.value} via {resolution.method.value}"


def _location_label(context: TextRefSourceContext) -> str | None:
    if context.start is None or context.end is None or context.resolved_span is None:
        return None
    start, end = context.resolved_span
    return (
        f"L{context.start.line}:C{context.start.column}-"
        f"L{context.end.line}:C{context.end.column} [{start}:{end})"
    )


def _bounded_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    head_length = max_chars // 2
    tail_length = max_chars - head_length
    elided = len(value) - max_chars
    return f"{value[:head_length]}... [{elided} chars elided] ...{value[-tail_length:]}"


def _target_evidence_lines(
    text_ref: TextRef,
    context: TextRefSourceContext,
    max_quote_chars: int,
) -> list[str]:
    if isinstance(text_ref.selector, PointSelector):
        return [f"Point affinity: {text_ref.selector.affinity.value}"]
    assert context.selected_source is not None
    return [f"Quote: {_json(_bounded_text(context.selected_source, max_quote_chars))}"]


def _render_source_lines(
    lines: Sequence[SourceLine],
    *,
    omitted_before: bool,
    omitted_after: bool,
    max_source_lines: int,
) -> list[str]:
    visible: list[SourceLine | None]
    if len(lines) <= max_source_lines:
        visible = list(lines)
    else:
        head_length = max_source_lines // 2
        tail_length = max_source_lines - head_length
        visible = [*lines[:head_length], None, *lines[-tail_length:]]
    width = len(str(lines[-1].number))
    result: list[str] = []
    if omitted_before:
        result.append("    ... earlier lines omitted ...")
    for line in visible:
        if line is None:
            hidden = len(lines) - max_source_lines
            result.append(f"    ... {hidden} lines elided ...")
        else:
            suffix = f" {line.text}" if line.text else ""
            result.append(f"    {line.number:>{width}} |{suffix}")
    if omitted_after:
        result.append("    ... later lines omitted ...")
    return result


def _merge_windows(
    records: Sequence[tuple[TextAnnotation, TextRefSourceContext]],
) -> list[_RenderWindow]:
    windows: list[_RenderWindow] = []
    ordered = sorted(
        records,
        key=lambda record: (
            record[1].lines[0].number if record[1].lines else 0,
            record[0].id,
        ),
    )
    for annotation, context in ordered:
        if not context.lines:
            continue
        start_line = context.lines[0].number
        end_line = context.lines[-1].number
        if windows and start_line <= windows[-1].end_line + 1:
            window = windows[-1]
            window.end_line = max(window.end_line, end_line)
            window.lines.update({line.number: line for line in context.lines})
            window.annotations.append((annotation, context))
        else:
            windows.append(
                _RenderWindow(
                    start_line=start_line,
                    end_line=end_line,
                    lines={line.number: line for line in context.lines},
                    annotations=[(annotation, context)],
                )
            )
    return windows


def _group_unresolved(
    records: Sequence[tuple[TextAnnotation, TextRefSourceContext]],
) -> dict[str, list[tuple[TextAnnotation, TextRefSourceContext]]]:
    groups: dict[str, list[tuple[TextAnnotation, TextRefSourceContext]]] = {}
    labels = {
        "missing": "Missing",
        "ambiguous": "Ambiguous",
        "boundary_mismatched": "Boundary mismatched",
        "unsupported": "Unsupported",
    }
    for record in records:
        resolution = record[1].resolution
        if resolution.document != DocumentStatus.resolved:
            heading = "Orphaned"
        else:
            heading = labels.get(resolution.selector.value, "Unsupported")
        groups.setdefault(heading, []).append(record)
    return groups


def _annotation_lines(
    annotation: TextAnnotation,
    context: TextRefSourceContext,
    max_quote_chars: int,
) -> list[str]:
    resolution = context.resolution
    lines = [
        f"- ID: {_json(annotation.id)}",
        f"  Motivations: {_json(annotation.motivations)}",
        f"  Target: {annotation.target.target_kind.value}",
        f"  URI: {_render_uri(annotation.target)}",
        f"  Resolution: {_resolution_label(resolution)}",
        f"  Source validation: {resolution.source_validation.value}",
    ]
    location = _location_label(context)
    if location is not None:
        lines.append(f"  Range: {location}")
    if context.selected_source is not None:
        lines.extend(
            f"  {line}"
            for line in _target_evidence_lines(annotation.target, context, max_quote_chars)
        )
    if resolution.candidates:
        candidates = ", ".join(
            f"[{candidate.start}:{candidate.end})" for candidate in resolution.candidates
        )
        lines.append(f"  Candidates: {candidates}")
    if annotation.body is not None:
        lines.append(f"  Body: {_json(annotation.body.value)}")
    if annotation.style is not None:
        lines.append(f"  Style: {_json(annotation.style)}")
    if annotation.tags:
        lines.append(f"  Tags: {_json(annotation.tags)}")
    if annotation.captured_text is not None:
        lines.append(f"  Captured text: {_json(annotation.captured_text)}")
    if annotation.provenance:
        lines.append(f"  Provenance: {_json(annotation.provenance)}")
    return lines
