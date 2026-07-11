"""
Document sections: a heading plus the content it owns, with nested subsections.
Built by `FlexDoc.sections()` from the structural heading blocks; see that method
for the construction rules.
"""

# pyright: reportImportCycles=false
# The TYPE_CHECKING import of FlexDoc creates a type-only cycle with flex_doc.py (which
# runtime-imports Section). No module-level runtime cycle exists.

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING

from flexdoc.docs.block_tree import Block, parse_blocks
from flexdoc.docs.links import NAVIGABLE_LINK_FORMS, Link, block_links
from flexdoc.docs.paragraphs import Paragraph, _size_paragraphs, _summarize_paragraphs
from flexdoc.docs.sizes import TextUnit

if TYPE_CHECKING:
    from flexdoc.docs.flex_doc import FlexDoc


@dataclass
class Section:
    """
    A document section: a heading plus the content it owns, with nested subsections.

    `content` are this section's own content paragraphs (excluding the heading line and
    any subsections); `children` are nested `Section`s. Built by `FlexDoc.sections()`.
    Sizes use the same private paragraph aggregation as `FlexDoc`, so every `TextUnit`
    aggregates uniformly without constructing a temporary document.

    Both views derive from this section's source region (nothing stored as counts):

    - the *structural* view — `blocks()` / `subtree_blocks()` — the density-invariant
      `Block` tree scoped to this section (its own content, or the whole subtree);
    - the *editing* view — `content`, `own_paragraphs()`, `subtree_paragraphs()` — the
      blank-line `Paragraph`s of the section's own region. For a well-formed document this
      matches the document's paragraph view; when a heading is glued to its body it is the
      per-region segmentation, so the body is owned by its heading rather than merged.

    `heading_block` (with parser-authoritative `HeadingInfo`) is the structural source of
    truth for the heading; `heading` is its projection into the editing view.

    `FlexDoc.sections()` returns an isolated copy of this graph because `content` and
    `heading` are editable `Paragraph`s. Mutating one returned section therefore changes
    only that returned view, never the document's cached section derivation.
    """

    heading_block: Block
    level: int
    content: list[Paragraph]
    children: list[Section]
    source_text: str = ""
    _doc: FlexDoc | None = field(default=None, compare=False, repr=False)
    # Heading-derived spans, set by `FlexDoc._section_list` (heading start to, respectively,
    # the next equal-or-higher heading and the very next heading of any level, trimmed). The
    # subtree `_span` nests by construction; `_own_span` bounds this section's own content (no
    # subsections). Both fall back to the paragraph extent for standalone sections. Derived,
    # so excluded from equality/repr.
    _span: tuple[int, int] | None = field(default=None, compare=False, repr=False)
    _own_span: tuple[int, int] | None = field(default=None, compare=False, repr=False)

    def _public_copy(self) -> Section:
        """Copy the editable paragraph graph without duplicating the owning document."""
        return Section(
            heading_block=self.heading_block,
            level=self.level,
            content=deepcopy(self.content),
            children=[child._public_copy() for child in self.children],
            source_text=self.source_text,
            _doc=self._doc,
            _span=self._span,
            _own_span=self._own_span,
        )

    def _all_blocks(self) -> list[Block]:
        """The whole-document structural parse, shared via the owning doc's cache when
        available (standalone sections fall back to a direct parse)."""
        if self._doc is not None:
            return self._doc.blocks()
        return parse_blocks(self.source_text)

    def _all_links(self) -> list[Link]:
        """The whole-document link list, shared via the owning doc's cache when
        available (standalone sections fall back to a direct parse)."""
        if self._doc is not None:
            return self._doc.links()
        return block_links(self.source_text, 0)

    @cached_property
    def heading(self) -> Paragraph:
        """The heading as an editing-view `Paragraph`, synthesized from `heading_block`'s
        exact source slice (the structural block, not the document's blank-line paragraph
        view, so a glued heading is never merged with its body)."""
        start, end = self.heading_block.span
        return Paragraph.from_text(self.source_text[start:end], start)

    @property
    def title(self) -> str:
        info = self.heading_block.heading_info
        return info.title if info is not None else ""

    def own_paragraphs(self) -> list[Paragraph]:
        """The heading plus this section's own content paragraphs (no subsections)."""
        return [self.heading, *self.content]

    @property
    def own_span(self) -> tuple[int, int]:
        """`[start, end)` of this section's own content (heading to the next heading of any
        level, trimmed); excludes subsections. Set by `FlexDoc._section_list`; falls back to
        the own-paragraph extent for standalone sections."""
        if self._own_span is not None:
            return self._own_span
        own = self.own_paragraphs()
        return own[0].span[0], own[-1].span[1]

    def blocks(self) -> list[Block]:
        """
        The structural block tree (see `FlexDoc.blocks`) restricted to this section's own
        content — the heading and the blocks it owns, excluding subsections. Spans are
        document-absolute and density-invariant like the whole-document tree, so per-section
        block-type tallies are spacing-independent (and correct for glued headings, since the
        scope is the structural `own_span`, not the blank-line paragraph extent).
        """
        start, end = self.own_span
        return [b for b in self._all_blocks() if start <= b.span[0] and b.span[1] <= end]

    def subtree_blocks(self) -> list[Block]:
        """
        The structural block tree restricted to this section's whole subtree (own content plus
        all subsections), scoped by `span`; the structural counterpart of
        `subtree_paragraphs()`.
        """
        start, end = self.span
        return [b for b in self._all_blocks() if start <= b.span[0] and b.span[1] <= end]

    def subtree_paragraphs(self) -> list[Paragraph]:
        """All paragraphs of this section and its subsections, in document order."""
        result = self.own_paragraphs()
        for child in self.children:
            result.extend(child.subtree_paragraphs())
        return result

    @property
    def span(self) -> tuple[int, int]:
        """`[start, end)` from the heading to the next same-or-higher heading (trimmed),
        when set by `FlexDoc._section_list`; otherwise the subtree-paragraph extent (for
        standalone sections). The heading-derived form guarantees sibling/parent spans nest
        and do not overlap, which the subtree extent cannot when a blank-line paragraph
        straddles a later heading."""
        if self._span is not None:
            return self._span
        paragraphs = self.subtree_paragraphs()
        return paragraphs[0].span[0], paragraphs[-1].span[1]

    def size(self, unit: TextUnit, subtree: bool = True) -> int:
        """
        Size in `unit`, rolled up over the whole subtree by default (`subtree=True`) or
        the section's own content only (`subtree=False`). Uses the same paragraph
        aggregation as `FlexDoc.size`.
        """
        paragraphs = self.subtree_paragraphs() if subtree else self.own_paragraphs()
        return _size_paragraphs(paragraphs, unit)

    def size_summary(self, subtree: bool = True) -> str:
        """Standard size summary for the subtree or this section's own content."""
        paragraphs = self.subtree_paragraphs() if subtree else self.own_paragraphs()
        return _summarize_paragraphs(paragraphs)

    def links(self) -> list[Link]:
        """
        All navigable links in this section's subtree (not images or reference
        definitions), in document order. Derived from a document-level parse of
        `source_text` (so reference links resolve across blocks) and filtered to links whose
        span falls within the section's span. Links with `span=None` (an unlocatable
        reference) are omitted because they cannot be attributed to a section by offset.
        """
        sec_start, sec_end = self.span
        return [
            link
            for link in self._all_links()
            if link.link_form in NAVIGABLE_LINK_FORMS
            and link.span is not None
            and sec_start <= link.span[0]
            and link.span[1] <= sec_end
        ]
