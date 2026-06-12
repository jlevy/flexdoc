"""
Document sections: a heading plus the content it owns, with nested subsections.
Built by `FlexDoc.sections()` from the structural heading blocks; see that method
for the construction rules.
"""

# pyright: reportImportCycles=false
# The TYPE_CHECKING/function-local imports of FlexDoc create a type-only cycle with
# flex_doc.py (which runtime-imports Section). No module-level runtime cycle exists.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from flexdoc.docs.block_tree import Block, parse_blocks
from flexdoc.docs.links import Link, block_links
from flexdoc.docs.paragraphs import Paragraph
from flexdoc.docs.sizes import TextUnit

if TYPE_CHECKING:
    from flexdoc.docs.flex_doc import FlexDoc


@dataclass
class Section:
    """
    A document section: a heading plus the content it owns, with nested subsections.

    `content` are this section's own content paragraphs (excluding the heading line and
    any subsections); `children` are nested `Section`s. Built by `FlexDoc.sections()`.
    Sizes are rolled up by reusing `FlexDoc.size` over the section's paragraphs, so every
    `TextUnit` aggregates uniformly.

    Two views of the same content, both derived (nothing stored as counts):

    - the *editing* view — `content`, `own_paragraphs()`, `subtree_paragraphs()` —
      returns the blank-line `Paragraph`s, matching the document's paragraph view;
    - the *structural* view — `blocks()` — returns the density-invariant structural
      `Block` tree scoped to this section.
    """

    heading: Paragraph
    level: int
    content: list[Paragraph]
    children: list[Section]
    source_text: str = ""
    _doc: FlexDoc | None = field(default=None, compare=False, repr=False)

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

    @property
    def title(self) -> str:
        return self.heading.heading_title() or ""

    def own_paragraphs(self) -> list[Paragraph]:
        """The heading plus this section's own content paragraphs (no subsections)."""
        return [self.heading, *self.content]

    def blocks(self) -> list[Block]:
        """
        The structural block tree (see `FlexDoc.blocks`) restricted to this section's
        own content — the heading and the blocks it owns, excluding subsections. Spans
        are document-absolute, and the slice is density-invariant like the whole-document
        tree, so per-section block-type tallies are spacing-independent.
        """
        own = self.own_paragraphs()
        start, end = own[0].span[0], own[-1].span[1]
        return [
            block for block in self._all_blocks() if start <= block.span[0] and block.span[1] <= end
        ]

    def subtree_paragraphs(self) -> list[Paragraph]:
        """All paragraphs of this section and its subsections, in document order."""
        result = self.own_paragraphs()
        for child in self.children:
            result.extend(child.subtree_paragraphs())
        return result

    @property
    def span(self) -> tuple[int, int]:
        """`[start, end)` covering the heading through the end of the last subtree
        paragraph."""
        paragraphs = self.subtree_paragraphs()
        return paragraphs[0].span[0], paragraphs[-1].span[1]

    def size(self, unit: TextUnit, subtree: bool = True) -> int:
        """
        Size in `unit`, rolled up over the whole subtree by default (`subtree=True`) or
        the section's own content only (`subtree=False`). Reuses `FlexDoc.size`.
        """
        # Local import: flex_doc imports Section, so a module-level import would cycle.
        from flexdoc.docs.flex_doc import FlexDoc

        paragraphs = self.subtree_paragraphs() if subtree else self.own_paragraphs()
        return FlexDoc(paragraphs).size(unit)

    def size_summary(self, subtree: bool = True) -> str:
        from flexdoc.docs.flex_doc import FlexDoc

        paragraphs = self.subtree_paragraphs() if subtree else self.own_paragraphs()
        return FlexDoc(paragraphs).size_summary()

    def links(self) -> list[Link]:
        """
        All links in this section's subtree, in document order. Derived from a
        document-level parse of `source_text` (so reference links resolve across
        blocks) and filtered to links whose span falls within the section's span.
        Links with `span=None` (e.g. reference definitions with no recoverable
        inline span) are omitted because they cannot be attributed to a section
        by offset alone.
        """
        sec_start, sec_end = self.span
        return [
            link
            for link in self._all_links()
            if link.span is not None and sec_start <= link.span[0] and link.span[1] <= sec_end
        ]
