# pyright: reportImportCycles=false
# Type-only cycles with node_table.py (TYPE_CHECKING import of FlexDoc) and sections.py
# (TYPE_CHECKING/function-local imports of FlexDoc). No runtime cycle exists.

from __future__ import annotations

import threading
from collections import defaultdict
from collections.abc import Callable, Generator, Iterable, Iterator
from copy import deepcopy
from dataclasses import dataclass, field
from functools import wraps
from typing import TypeVar, cast

import regex
from flowmark import flowmark_markdown
from funlog import tally_calls
from marko.block import Document
from typing_extensions import override

from flexdoc.docs.base_blocks import BaseBlock, base_blocks
from flexdoc.docs.block_tree import Block, parse_blocks, walk_blocks
from flexdoc.docs.block_types import BlockType
from flexdoc.docs.collect import collect as _collect
from flexdoc.docs.doc_graph import DEFAULT_INCLUDE, Detail, DocGraph, build_doc_graph
from flexdoc.docs.frontmatter import split_frontmatter
from flexdoc.docs.links import TRUE_LINK_FORMS, Link, LinkForm, block_links
from flexdoc.docs.node import Layer, Node, NodeKind, NodeTable
from flexdoc.docs.node_table import build_node_table
from flexdoc.docs.paragraphs import (
    Offsets,
    Paragraph,
    Sentence,
    SentenceMapping,
    SentIndex,
    Splitter,
    WordtokMapping,
    default_sentence_splitter,
)
from flexdoc.docs.sections import Section
from flexdoc.docs.sizes import TextUnit, size_in_bytes
from flexdoc.docs.wordtoks import (
    BOF_TOK,
    EOF_TOK,
    PARA_BR_STR,
    PARA_BR_TOK,
    SENT_BR_STR,
    join_wordtoks,
)
from flexdoc.util.token_estimate import estimate_tokens

_PARA_BREAK_REGEX = regex.compile(r"(?:[ \t\r]*\n){2,}[ \t\r]*")
r"""
A paragraph break: a run of whitespace containing two or more newlines (a blank
line). Blank lines that contain only spaces, tabs, or `\r` still count, and any
number of consecutive blank lines collapse into a single break.
"""


def _rstrip(text: str, lo: int, hi: int) -> int:
    """The largest `end` in `(lo, hi]` with no trailing whitespace (or `lo` if the range is
    all whitespace), so a heading-derived section span ends at its last non-space content,
    matching the structural block tree's trimmed spans."""
    while hi > lo and text[hi - 1].isspace():
        hi -= 1
    return hi


def _segment_paragraphs(
    source: str,
    start: int,
    end: int,
    sentence_splitter: Splitter = default_sentence_splitter,
) -> list[Paragraph]:
    """
    Segment `source[start:end]` into blank-line `Paragraph`s with absolute document offsets.

    The document's paragraph rule (a blank line is two or more newlines), factored out of
    `from_text` so a `Section` can derive the editing view of its own structural region.
    Segmenting per region — rather than bucketing the whole document's paragraphs by heading
    offset — is what makes section content correct when a heading is glued to its body: the
    document-level split would merge a glued heading, its body, and the next heading into one
    paragraph, while the per-region split owns exactly the region's content.
    """
    region = source[start:end]
    spans: list[tuple[int, int]] = []
    cursor = 0
    for m in _PARA_BREAK_REGEX.finditer(region):
        spans.append((cursor, m.start()))
        cursor = m.end()
    spans.append((cursor, len(region)))
    paragraphs: list[Paragraph] = []
    for span_start, span_end in spans:
        piece = region[span_start:span_end]
        stripped = piece.strip()
        if stripped:
            # Absolute offset of the stripped content within `source`.
            doc_offset = start + span_start + (len(piece) - len(piece.lstrip()))
            paragraphs.append(Paragraph.from_text(stripped, doc_offset, sentence_splitter))
    return paragraphs


# Inline kinds stripped from prose: code spans, links/images (kept as their text/alt),
# inline-HTML tags, and footnote references. See `FlexDoc.prose_text`.
_PROSE_INLINE_KINDS: frozenset[NodeKind] = frozenset(
    {
        NodeKind.link,
        NodeKind.image,
        NodeKind.code_span,
        NodeKind.inline_html,
        NodeKind.footnote_ref,
    }
)
_ATX_OPEN_REGEX = regex.compile(r"^[ \t]*#{1,6}[ \t]+")
_ATX_CLOSE_REGEX = regex.compile(r"[ \t]+#+[ \t]*$")
_BLOCK_MARKER_REGEX = regex.compile(r"^[ \t]*(?:>[ \t]?|[-*+][ \t]+|\d+[.)][ \t]+)+")
r"""Leading blockquote/list markers on a line (`>`, `-`/`*`/`+`, `1.`/`1)`), possibly nested
(`> - `); stripped from `prose_text()` so quoted and list prose reads as prose."""
_TABLE_SEPARATOR_REGEX = regex.compile(r"^[ \t]*\|?[ \t:|-]*-[ \t:|-]*\|?[ \t]*$")
r"""A Markdown table header/body separator row (e.g. `| --- | :-: |`); dropped when
`prose_text(include_tables=True)` flattens a table to its cell text."""


_DerivedT = TypeVar("_DerivedT")


def _memoized_derivation(
    attr_name: str,
) -> Callable[[Callable[[FlexDoc], _DerivedT]], Callable[[FlexDoc], _DerivedT]]:
    """
    Memoize a zero-arg `FlexDoc` derivation into `attr_name`, computed at most once.

    Filling the cache is the only state change that happens during a read, and it is
    idempotent and thread-safe: a lock-free fast path returns an already-cached value,
    otherwise the instance's reentrant lock serializes the first computation so
    concurrent readers compute it once and all observe the same object. This is sound
    only because every memoized derivation is a pure, deterministic function of the
    immutable-after-parse `source_text` (see the `FlexDoc` contract); the lock is
    reentrant so a derivation may call other memoized derivations (e.g. `node_table()`
    uses `blocks()` and `links()`).
    """

    def decorator(func: Callable[[FlexDoc], _DerivedT]) -> Callable[[FlexDoc], _DerivedT]:
        @wraps(func)
        def wrapper(self: FlexDoc) -> _DerivedT:
            cached = getattr(self, attr_name)
            if cached is not None:
                return cached
            with self._cache_lock:
                cached = getattr(self, attr_name)
                if cached is None:
                    cached = func(self)
                    setattr(self, attr_name, cached)
                return cached

        return wrapper

    return decorator


def _strip_heading_markers(text: str) -> str:
    """Remove ATX markers (`## `, trailing ` ##`) and a trailing setext underline so a
    heading block's text reads as plain prose."""
    text = _ATX_OPEN_REGEX.sub("", text)
    text = _ATX_CLOSE_REGEX.sub("", text)
    lines = text.splitlines()
    if len(lines) >= 2:
        underline = lines[-1].strip()
        if underline and len(set(underline)) == 1 and underline[0] in "=-":
            text = "\n".join(lines[:-1])
    return text


def _strip_block_markers(text: str) -> str:
    """Strip leading blockquote (`>`) and list (`-`/`*`/`+`/`1.`) markers from each line so
    quoted and list prose reads as plain prose; nested markers (`> -`) are removed together."""
    return "\n".join(_BLOCK_MARKER_REGEX.sub("", line) for line in text.splitlines())


def _table_prose_text(text: str) -> str:
    """Flatten an (already inline-stripped) Markdown table slice to prose: drop the
    header/body separator row and join each row's cell text with spaces, one row per line."""
    rows: list[str] = []
    for line in text.splitlines():
        if _TABLE_SEPARATOR_REGEX.match(line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        row = " ".join(cell for cell in cells if cell)
        if row:
            rows.append(row)
    return "\n".join(rows)


@dataclass
class FlexDoc:
    """
    A parsed document: one retained source string plus its layered projections.
    `FlexDoc.from_text(text)` parses Markdown (with or without embedded HTML) into the
    blank-line editing view (paragraphs and sentences, with exact source offsets) and
    derives the structural views on demand: `blocks()`, `sections()`, `links()`,
    `base_blocks()`, the node table, `collect()`, and `graph()`.

    Contract and intended use:

    - A `FlexDoc` is a snapshot of a *parsed source document*, meant for analysis
      (sizing, classifying, diffing, windowing) and for generating *new* text via
      `reassemble()`. It is not a live, self-updating DOM.

    - Source references are fixed at parse time. `Paragraph.original_text` and the
      `offsets` on paragraphs and sentences point back into the text passed to
      `from_text`, but `from_text` stores stripped block text and `reassemble()`
      normalizes paragraph separators. Use these references for source mapping, not as
      a byte-for-byte full-document preservation model. They are not updated when
      content is mutated, so they remain valid as references back to the source.

    - Offsets: every paragraph and sentence carries an `Offsets` record with both
      `doc_offset` (absolute in the document) and `block_offset` (relative to the
      enclosing block — the document for a paragraph, the paragraph for a sentence).

    - In-place editing is supported for *building transformed output*: mutate
      sentence text (`replace_str`, `set_sent`) or restructure the paragraph and
      sentence lists (`sub_doc`, `sub_paras`, `filtered`, `append_sent`), then call
      `reassemble()`. This is safe as long as you do not rely on the source
      references tracking your edits: after editing, `original_text`, the `offsets`,
      and cached values like `Paragraph.block_type` still describe the *original*
      blocks. To get offsets/classification for edited content, re-parse with
      `FlexDoc.from_text(doc.reassemble())`.

    - `filtered()` returns an independent deep copy; `iter_paragraphs()` and the
      `paragraphs`/`sentences` lists expose this document's live objects.

    - `source_text` is the document text the offsets index into. For a parsed doc it is
      the unmodified input; `sub_doc`/`sub_paras`/`filtered` carry the same `source_text`
      (their offsets still point into it). Docs built from synthetic content
      (`from_wordtoks`) set it to the reassembled text. `paragraph_at_offset` /
      `sentence_at_offset` map an absolute offset back to the unit that contains it.

    - Read-time thread-safety. The derived views — `blocks()`, `links()`, `sections()`,
      `base_blocks()`, `node_table()`, `graph()`, `collect()`, and the size/TOC helpers —
      are read-only with respect to your data: they are pure, deterministic functions of
      `source_text` and never mutate paragraphs or sentences. The *only* state change
      during such a read is idempotent population of internal caches. The document-level
      caches (the shared marko parse, the block tree, the link list, the section tree,
      the node table) are filled under a per-instance reentrant lock, so concurrent
      readers compute each at
      most once and all observe the same value. A few per-element values (e.g.
      `Paragraph.block_type`) are memoized with `cached_property`, which is not lock-
      guarded but is equally idempotent and deterministic — a pure function of that
      element's immutable `original_text` — so a concurrent recompute is harmless (it
      yields the same value). Because every derivation is deterministic, the result is
      identical whether or not a cache was warm and regardless of read order. The
      *editing* methods (`set_sent`, `replace_str`, `append_sent`, `sub_doc`, `filtered`,
      etc.) do mutate and are not thread-safe; do not edit a document while another thread
      reads it. Editing also does not invalidate the source-backed caches (they remain
      keyed to the parsed `source_text`); re-parse with `from_text(doc.reassemble())` to
      analyze edited content.
    """

    paragraphs: list[Paragraph]
    source_text: str = ""
    # Reentrant lock guarding idempotent cache population (see the class contract and
    # `_memoized_derivation`). Per-instance so reads of different documents never contend;
    # reentrant so a derivation may use other memoized derivations.
    _cache_lock: threading.RLock = field(
        default_factory=threading.RLock, init=False, compare=False, repr=False
    )
    _cached_parsed: Document | None = field(default=None, init=False, compare=False, repr=False)
    _cached_node_table: NodeTable | None = field(
        default=None, init=False, compare=False, repr=False
    )
    _cached_blocks: list[Block] | None = field(default=None, init=False, compare=False, repr=False)
    _cached_links: list[Link] | None = field(default=None, init=False, compare=False, repr=False)
    _cached_sections: list[Section] | None = field(
        default=None, init=False, compare=False, repr=False
    )

    @override
    def __getstate__(self) -> dict[str, object]:
        # Pickle/deepcopy only the source data. The reentrant lock is not pickleable and
        # the derived caches (incl. the marko parse) re-derive on demand, so both are
        # dropped here and recreated in `__setstate__`. This keeps `FlexDoc` copyable and
        # picklable despite holding a lock.
        return {"paragraphs": self.paragraphs, "source_text": self.source_text}

    def __setstate__(self, state: dict[str, object]) -> None:
        self.paragraphs = cast("list[Paragraph]", state["paragraphs"])
        self.source_text = cast(str, state["source_text"])
        self._cache_lock = threading.RLock()
        self._cached_parsed = None
        self._cached_node_table = None
        self._cached_blocks = None
        self._cached_links = None
        self._cached_sections = None

    @_memoized_derivation("_cached_parsed")
    def _parsed(self) -> Document:
        """
        The single shared marko parse of `source_text`, computed once. `blocks()` and
        `links()` (and `base_blocks()`) derive from this one parse rather than each
        re-parsing the whole document. See the class contract on read-time caching.
        """
        return flowmark_markdown().parse(self.source_text or self.reassemble())

    @_memoized_derivation("_cached_node_table")
    def node_table(self) -> NodeTable:
        """
        The node table for this document, computed once and cached. A pure function of
        the immutable `source_text` (see the class contract on read-time caching).
        """
        return build_node_table(self)

    @classmethod
    @tally_calls(level="warning", min_total_runtime=5)
    def from_text(
        cls, text: str, sentence_splitter: Splitter = default_sentence_splitter
    ) -> FlexDoc:
        """
        Parse a document from a string. Paragraphs are split on blank lines (two or
        more newlines, including blank lines that contain only whitespace). The
        stored block strips surrounding whitespace, so offsets point to the stored
        block content inside `text`: for each paragraph, the slice starting at
        `p.offsets.doc_offset` with length `len(p.original_text)` round-trips to
        `p.original_text`. `reassemble()` produces normalized editable text, not a
        byte-for-byte copy of the full input.
        """
        # A leading YAML frontmatter block is isolated as a non-content region: paragraphs
        # (and thus sentences, sizes, and prose counts) are built over the body only, with
        # absolute offsets into the full `text` (kept as `source_text`). See `frontmatter`.
        _raw, content_offset = split_frontmatter(text)
        paragraphs = _segment_paragraphs(text, content_offset, len(text), sentence_splitter)
        return cls(paragraphs=paragraphs, source_text=text)

    @property
    def frontmatter(self) -> str | None:
        """
        The verbatim leading YAML frontmatter block (both `---` delimiters included), or
        `None` if the document has none. Frontmatter is a non-content region: excluded from
        `paragraphs`, `blocks()`, `sections()`, the node table, and every size/prose count,
        but `source_text` retains it so the document round-trips.
        """
        return split_frontmatter(self.source_text)[0]

    def _content_offset(self) -> int:
        """Offset into `source_text` where the body (post-frontmatter content) begins;
        0 when there is no frontmatter."""
        return split_frontmatter(self.source_text)[1]

    @classmethod
    def from_wordtoks(cls, wordtoks: list[str]) -> FlexDoc:
        """
        Parse a document from a list of wordtoks.
        """
        return FlexDoc.from_text(join_wordtoks(wordtoks))

    def reassemble(self) -> str:
        """
        Reassemble the document from its paragraphs.
        """
        return PARA_BR_STR.join(paragraph.reassemble() for paragraph in self.paragraphs)

    def replace_str(self, old: str, new: str):
        for para in self.paragraphs:
            para.replace_str(old, new)

    def first_index(self) -> SentIndex:
        return SentIndex(0, 0)

    def last_index(self) -> SentIndex:
        return SentIndex(len(self.paragraphs) - 1, len(self.paragraphs[-1].sentences) - 1)

    def para_iter(self, reverse: bool = False) -> Iterable[tuple[int, Paragraph]]:
        enum_paras = list(enumerate(self.paragraphs))
        return reversed(enum_paras) if reverse else enum_paras

    def sent_iter(self, reverse: bool = False) -> Iterable[tuple[SentIndex, Sentence]]:
        for para_index, para in self.para_iter(reverse=reverse):
            for sent_index, sent in para.sent_iter(reverse=reverse):
                yield SentIndex(para_index, sent_index), sent

    def paragraph_at_offset(self, offset: int) -> Paragraph | None:
        """
        The paragraph whose span contains `offset` (an absolute character offset into
        the source), or `None` if `offset` falls in inter-paragraph whitespace or
        outside the document. (For the structural layer, query `blocks()` spans or use
        `collect(overlaps=...)`.)
        """
        for para in self.paragraphs:
            start, end = para.span
            if start <= offset < end:
                return para
        return None

    def sentence_at_offset(self, offset: int) -> SentIndex | None:
        """
        The `SentIndex` of the sentence whose span contains `offset`, or `None` if none
        does (inter-block/inter-sentence whitespace, or outside the document).
        """
        for para_index, para in enumerate(self.paragraphs):
            p_start, p_end = para.span
            if not (p_start <= offset < p_end):
                continue
            for sent_index, sent in enumerate(para.sentences):
                start, end = sent.span
                if start <= offset < end:
                    return SentIndex(para_index, sent_index)
            return None
        return None

    def block_at_offset(self, offset: int) -> Block | None:
        """
        The innermost structural `Block` whose span contains `offset` (half-open:
        `start <= offset < end`), or `None` if `offset` falls outside every block
        (inter-block whitespace, frontmatter, or out of range). Descends into nested blocks
        (list items, blockquotes) to return the narrowest container — the structural
        counterpart of `paragraph_at_offset`.
        """
        match: Block | None = None
        blocks = self.blocks()
        while blocks:
            for block in blocks:
                start, end = block.span
                if start <= offset < end:
                    match = block
                    blocks = block.children
                    break
            else:
                break
        return match

    def sections(self) -> list[Section]:
        """
        The heading hierarchy as a tree of top-level `Section`s. A section owns the
        blocks from its heading up to the next heading of equal-or-higher level; deeper
        headings become nested `children`. Content before the first heading (preamble)
        belongs to no section.

        Headings come from the structural parse — top-level `heading` blocks of
        `blocks()` — not the blank-line paragraph view, so a `#`-prefixed line that the
        paragraph splitter isolates from inside a fenced code block is not mistaken for a
        section heading, and headings nested in blockquotes or list items (which are not
        top-level blocks) do not start document sections.

        Computed once and cached (see the class contract on read-time caching). Returns
        a fresh shallow copy of the cached root list each call; the `Section` objects
        themselves are shared and must be treated as read-only.
        """
        return list(self._section_list())

    @_memoized_derivation("_cached_sections")
    def _section_list(self) -> list[Section]:
        # Sections derive entirely from the top-level structural `heading` blocks (spec
        # section 7): each heading owns the structural region from its end to the next heading
        # of any level (its own content), and nests under the most recent heading of a lower
        # level. Both the heading set and the owned content come from the block tree, not the
        # blank-line paragraph view, so a heading glued to its body (tight) or preceded by a
        # non-blank line (marker) still owns exactly its content — the paragraph view merges a
        # glued heading with its body and cannot attribute it.
        source_text = self.source_text or self.reassemble()
        heading_blocks = [b for b in self.blocks() if b.type == BlockType.heading]
        if not heading_blocks:
            return []

        starts = [b.span[0] for b in heading_blocks]
        levels = [b.heading_level or 1 for b in heading_blocks]
        n = len(heading_blocks)
        roots: list[Section] = []
        stack: list[Section] = []
        for i, block in enumerate(heading_blocks):
            level = levels[i]
            # Subtree span: heading to the next heading of equal-or-higher level (nests by
            # construction). Own span: heading to the very next heading of ANY level —
            # everything past it is a subsection or a later section, never own content.
            subtree_end = next(
                (starts[j] for j in range(i + 1, n) if levels[j] <= level), len(source_text)
            )
            own_end = starts[i + 1] if i + 1 < n else len(source_text)
            span = (block.span[0], _rstrip(source_text, block.span[1], subtree_end))
            own_span = (block.span[0], _rstrip(source_text, block.span[1], own_end))
            section = Section(
                heading_block=block,
                level=level,
                content=_segment_paragraphs(source_text, block.span[1], own_span[1]),
                children=[],
                source_text=source_text,
                _doc=self,
                _span=span,
                _own_span=own_span,
            )
            while stack and stack[-1].level >= level:
                stack.pop()
            (stack[-1].children if stack else roots).append(section)
            stack.append(section)
        return roots

    @_memoized_derivation("_cached_links")
    def _link_list(self) -> list[Link]:
        source_text = self.source_text or self.reassemble()
        content_offset = self._content_offset()
        if content_offset:
            return block_links(source_text[content_offset:], content_offset)
        return block_links(source_text, 0, parsed=self._parsed())

    def links(self, *, link_forms: set[LinkForm] | None = None) -> list[Link]:
        """
        Links in the document, in document order. By default returns only navigable links
        (`TRUE_LINK_FORMS`: inline, reference, autolink, bare URL); pass `link_forms` to
        select any `LinkForm`s instead — e.g. `links(link_forms={LinkForm.image})` for
        images, or `links(link_forms={LinkForm.reference_definition})` for `[id]: url`
        definitions. Use `images()` for the common image case.

        Derived from the document's single shared parse (see the class contract on
        read-time caching), so reference-style links (`[text][ref]` with `[ref]: url` in a
        separate block) resolve correctly. Returns a fresh list each call so mutating the
        result cannot poison the cache (`Link` is frozen, so the shared elements are safe).
        See `Link`.
        """
        selected = TRUE_LINK_FORMS if link_forms is None else link_forms
        return [link for link in self._link_list() if link.link_form in selected]

    def images(self) -> list[Link]:
        """
        All images (`![alt](url)`), in document order; a convenience for
        `links(link_forms={LinkForm.image})`. For each, `text` is the alt text. See `Link`.
        """
        return self.links(link_forms={LinkForm.image})

    def prose_text(self, *, include_tables: bool = False) -> str:
        """
        Prose-only text for editorial linting and prose metrics: the readable prose of the
        document with both inline markup and non-prose blocks removed. This is a prose
        *projection*, not a faithful plain-text rendering of the whole document — code blocks,
        HTML blocks, thematic breaks, reference-definition lines, and frontmatter are dropped
        entirely (not flattened to text), and tables are dropped unless `include_tables=True`
        (then each table is flattened to its cell text, one row per line).

        Included blocks are paragraphs and headings, including those nested in lists and
        blockquotes. Within each block the inline markup is removed: inline code, footnote
        references, and inline-HTML tags are dropped (the text an HTML tag wraps is kept, so
        `<span>foo</span> bar` becomes `foo bar`); links and images become their text/alt.
        Leading markers are stripped — heading `#`/setext underlines, blockquote `>`, and
        list `-`/`*`/`1.` — so the result reads as plain prose.

        Line wrapping is preserved, not normalized: a block's source line breaks are kept
        verbatim (hard-wrapped prose stays wrapped — `prose_text()` never reflows or joins
        wrapped lines), and blocks are separated by a single blank line. Slices come from the
        verbatim source (not `reassemble()`), so editorial spacing such as a spaced em-dash
        (`" — "`) survives exactly. Depends only on the node table, so it is a pure function
        of `source_text` (see the class contract on read-time caching).
        """
        table = self.node_table()
        source = self.source_text or self.reassemble()
        # Reference-definition lines (`[id]: url`) are structurally their own blocks but are
        # not prose; drop any block covered by a `link_ref_def` node so definition ids and
        # URLs do not leak into the editorial-lint text.
        ref_def_spans = [
            n.source_span
            for n in table.nodes.values()
            if n.kind == NodeKind.link_ref_def and n.source_span is not None
        ]
        included = {BlockType.paragraph, BlockType.heading}
        if include_tables:
            included.add(BlockType.table)
        parts: list[str] = []
        for block, _depth in walk_blocks(self.blocks()):
            if block.type not in included:
                continue
            if any(rs[0] <= block.span[0] and block.span[1] <= rs[1] for rs in ref_def_spans):
                continue
            if block.type == BlockType.table:
                text = _table_prose_text(self._block_prose_text(block, table, source))
            else:
                text = _strip_block_markers(self._block_prose_text(block, table, source))
                if block.type == BlockType.heading:
                    text = _strip_heading_markers(text)
            text = text.strip()
            if text:
                parts.append(text)
        return "\n\n".join(parts)

    def _block_prose_text(self, block: Block, table: NodeTable, source: str) -> str:
        """A prose block's source slice with inline non-prose spans replaced (links/images
        by their text/alt) or dropped (code spans, inline-HTML tags, footnote refs)."""
        b_start, b_end = block.span
        inlines = sorted(
            (
                n
                for n in table.nodes.values()
                if n.layer == Layer.markdown
                and n.kind in _PROSE_INLINE_KINDS
                and n.source_span is not None
                and b_start <= n.source_span[0]
                and n.source_span[1] <= b_end
            ),
            key=lambda n: (n.source_span[0], n.source_span[1]),  # pyright: ignore[reportOptionalSubscript]
        )
        out: list[str] = []
        cursor = b_start
        for node in inlines:
            assert node.source_span is not None
            start, end = node.source_span
            # Skip an inline nested inside an already-substituted one (e.g. an image inside
            # a linked image): its enclosing node's replacement text already covers it.
            if start < cursor:
                continue
            out.append(source[cursor:start])
            if node.kind in (NodeKind.link, NodeKind.image):
                text = node.attrs.get("text")
                out.append(text if isinstance(text, str) else "")
            cursor = end
        out.append(source[cursor:b_end])
        # Collapse horizontal whitespace left where an inline span was dropped (e.g. the
        # space pair around a removed code span). Single spaces, including a spaced em-dash
        # `" — "`, are untouched; newlines are preserved.
        return regex.sub(r"[^\S\n]{2,}", " ", "".join(out))

    @_memoized_derivation("_cached_blocks")
    def _block_list(self) -> list[Block]:
        blocks = parse_blocks(self.source_text or self.reassemble(), self._parsed())
        # Exclude any block in the leading frontmatter region (a non-content region; see
        # `frontmatter`). Frontmatter parses into top-level blocks before the body, so a
        # span-start guard drops them without disturbing the body's absolute spans.
        content_offset = self._content_offset()
        if content_offset:
            blocks = [b for b in blocks if b.span[0] >= content_offset]
        return blocks

    def blocks(self) -> list[Block]:
        """
        The document's structural block tree (opt-in), with exact source spans. Unlike
        the blank-line `paragraphs`, this keeps a fenced code block whole (even with
        internal blank lines) and decomposes a tight list into `list_item`s with nested
        sublists. Derived from the document's single shared parse (see the class contract
        on read-time caching), so `sections()`, `links()`, and the node table all reuse
        one parse. See `flexdoc.docs.block_tree`.

        Returns a fresh shallow copy of the cached list each call, so reordering/filtering
        the result cannot poison the shared cache; the `Block` objects themselves are
        shared and must be treated as read-only.
        """
        return list(self._block_list())

    def base_blocks(self, *, item_partition_depth: int = 6) -> list[BaseBlock]:
        """
        The flat, depth-annotated sequential base-block partition of the document: a
        complete, ordered, non-overlapping cover whose reassembly reproduces the source
        (except normalized paragraph-break whitespace). A thin method over the
        `flexdoc.docs.base_blocks.base_blocks` free function; see it for the
        `item_partition_depth` semantics. Distinct from `blocks()`, which is the
        recursive structural tree (a query view, not a partition). Reuses the document's
        single shared parse.
        """
        partition = base_blocks(
            self.source_text or self.reassemble(),
            item_partition_depth=item_partition_depth,
            parsed=self._parsed(),
        )
        # Drop the leading frontmatter region (see `frontmatter`); it is not content, so it
        # is not part of the document's base-block partition.
        content_offset = self._content_offset()
        if content_offset:
            partition = [bb for bb in partition if bb.block.span[0] >= content_offset]
        return partition

    def toc(self) -> list[tuple[int, str, tuple[int, int]]]:
        """Flat table of contents in document order: `(level, title, span)` per heading."""
        entries: list[tuple[int, str, tuple[int, int]]] = []

        def walk(sections: list[Section]) -> None:
            for section in sections:
                entries.append((section.level, section.title, section.span))
                walk(section.children)

        walk(self.sections())
        return entries

    def section_size_tree(self, units: tuple[TextUnit, ...] = (TextUnit.words,)) -> str:
        """
        Render the section hierarchy as an indented tree with rolled-up sizes per
        section (each line covers the section and all its subsections).
        """
        lines: list[str] = []

        def walk(sections: list[Section], depth: int) -> None:
            for section in sections:
                sizes = ", ".join(f"{section.size(unit)} {unit.value}" for unit in units)
                lines.append(f"{'  ' * depth}{'#' * section.level} {section.title}  ({sizes})")
                walk(section.children, depth + 1)

        walk(self.sections(), 0)
        return "\n".join(lines)

    def get_sent(self, index: SentIndex) -> Sentence:
        return self.paragraphs[index.para_index].sentences[index.sent_index]

    def set_sent(self, index: SentIndex, sent_str: str) -> None:
        # Preserve the replaced sentence's `original_text` so its `span` keeps
        # pointing at the original source slice (the documented contract: source
        # references describe the original blocks, not the edited content, which
        # lives in `text`). Dropping it would make `span` describe the new text's
        # length at the old offset, i.e. neither the old nor a valid source slice.
        old_sent = self.get_sent(index)
        self.paragraphs[index.para_index].sentences[index.sent_index] = Sentence(
            sent_str, old_sent.offsets, original_text=old_sent.original_text
        )

    def seek_to_sent(self, offset: int, unit: TextUnit) -> tuple[SentIndex, int]:
        """
        Find the last sentence that starts before a given offset. Returns the SentIndex
        and the offset of the sentence start in the original document.
        """
        current_size = 0
        last_fit_index = None
        last_fit_offset = 0

        if unit == TextUnit.bytes:
            size_sent_break = size_in_bytes(SENT_BR_STR)
            size_para_break = size_in_bytes(PARA_BR_STR)
        elif unit == TextUnit.chars:
            size_sent_break = len(SENT_BR_STR)
            size_para_break = len(PARA_BR_STR)
        elif unit == TextUnit.words:
            size_sent_break = 0
            size_para_break = 0
        elif unit == TextUnit.wordtoks:
            size_sent_break = 1
            size_para_break = 1
        else:
            raise NotImplementedError(f"Unsupported unit for seek_doc: {unit}")

        for para_index, para in enumerate(self.paragraphs):
            for sent_index, sent in enumerate(para.sentences):
                sentence_size = sent.size(unit)
                last_fit_index = SentIndex(para_index, sent_index)
                last_fit_offset = current_size
                if current_size + sentence_size + size_sent_break <= offset:
                    current_size += sentence_size
                    if sent_index < len(para.sentences) - 1:
                        current_size += size_sent_break
                else:
                    return last_fit_index, last_fit_offset
            if para_index < len(self.paragraphs) - 1:
                current_size += size_para_break

        if last_fit_index is None:
            raise ValueError("Cannot seek into empty document")

        return last_fit_index, last_fit_offset

    def sub_doc(self, first: SentIndex, last: SentIndex | None = None) -> FlexDoc:
        """
        Get a sub-document. Inclusive ranges. Preserves original paragraph and sentence offsets.
        """
        if not last:
            last = self.last_index()
        if last > self.last_index():
            raise ValueError(f"End index out of range: {last} > {self.last_index()}")
        if first < self.first_index():
            raise ValueError(f"Start index out of range: {first} < {self.first_index()}")

        sub_paras: list[Paragraph] = []
        for i in range(first.para_index, last.para_index + 1):
            para = self.paragraphs[i]
            if i == first.para_index and i == last.para_index:
                sub_paras.append(
                    Paragraph(
                        original_text=para.original_text,
                        sentences=para.sentences[first.sent_index : last.sent_index + 1],
                        offsets=para.offsets,
                    )
                )
            elif i == first.para_index:
                sub_paras.append(
                    Paragraph(
                        original_text=para.original_text,
                        sentences=para.sentences[first.sent_index :],
                        offsets=para.offsets,
                    )
                )
            elif i == last.para_index:
                sub_paras.append(
                    Paragraph(
                        original_text=para.original_text,
                        sentences=para.sentences[: last.sent_index + 1],
                        offsets=para.offsets,
                    )
                )
            else:
                sub_paras.append(para)

        # Deep-copy so the sub-document is an independent value: callers (and transform
        # helpers like remove_window_br) must not mutate the original through a slice.
        return FlexDoc([deepcopy(p) for p in sub_paras], source_text=self.source_text)

    def sub_paras(self, start: int, end: int | None = None) -> FlexDoc:
        """
        Get a sub-document containing a range of paragraphs. Returns an independent deep
        copy, so mutating the sub-document does not affect this one.
        """
        if end is None:
            end = len(self.paragraphs) - 1
        return FlexDoc(
            [deepcopy(p) for p in self.paragraphs[start : end + 1]],
            source_text=self.source_text,
        )

    def iter_paragraphs(
        self,
        *,
        include: set[BlockType] | None = None,
        exclude: set[BlockType] | None = None,
    ) -> Iterator[Paragraph]:
        """
        Iterate over this document's paragraphs (the blank-line editing view),
        optionally filtering by each paragraph's `BlockType` classification.
        `include` keeps only the given types; `exclude` drops the given types. If
        both are given, a paragraph must be in `include` and not in `exclude`.

        Yields this document's own `Paragraph` objects (not copies), so in-place
        edits such as `replace_str` affect this document. Use `filtered` for an
        independent sub-document.
        """
        for para in self.paragraphs:
            block_type = para.block_type
            if include is not None and block_type not in include:
                continue
            if exclude is not None and block_type in exclude:
                continue
            yield para

    def filtered(
        self,
        *,
        include: set[BlockType] | None = None,
        exclude: set[BlockType] | None = None,
    ) -> FlexDoc:
        """
        Return a new sub-document containing only the paragraphs matching the given
        `BlockType` filter, e.g.
        `doc.filtered(include={BlockType.paragraph}).size(TextUnit.words)` gives
        the total words across all prose paragraphs.

        The returned document deep-copies the matched paragraphs, so it is independent
        of this document: editing one does not affect the other. (Use `iter_paragraphs`
        to edit this document's paragraphs in place.)
        """
        return FlexDoc(
            [deepcopy(para) for para in self.iter_paragraphs(include=include, exclude=exclude)],
            source_text=self.source_text,
        )

    def prev_sent(self, index: SentIndex) -> SentIndex:
        if index.sent_index > 0:
            return SentIndex(index.para_index, index.sent_index - 1)
        elif index.para_index > 0:
            return SentIndex(
                index.para_index - 1,
                len(self.paragraphs[index.para_index - 1].sentences) - 1,
            )
        else:
            raise ValueError("No previous sentence")

    def append_sent(self, sent: Sentence) -> None:
        if len(self.paragraphs) == 0:
            self.paragraphs.append(
                Paragraph(original_text=sent.text, sentences=[sent], offsets=Offsets(0, 0))
            )
        else:
            last_para = self.paragraphs[-1]
            last_para.sentences.append(sent)

    def size(self, unit: TextUnit) -> int:
        if unit == TextUnit.paragraphs:
            return len(self.paragraphs)
        if unit == TextUnit.sentences:
            return sum(len(para.sentences) for para in self.paragraphs)

        if unit == TextUnit.tokens:
            return estimate_tokens(self.reassemble())

        base_size = sum(para.size(unit) for para in self.paragraphs)
        n_para_breaks = max(len(self.paragraphs) - 1, 0)
        if unit == TextUnit.lines:
            return base_size + n_para_breaks
        if unit == TextUnit.bytes:
            return base_size + n_para_breaks * size_in_bytes(PARA_BR_STR)
        if unit == TextUnit.chars:
            return base_size + n_para_breaks * len(PARA_BR_STR)
        if unit == TextUnit.words:
            return base_size
        if unit == TextUnit.wordtoks:
            return base_size + n_para_breaks

        raise ValueError(f"Unsupported unit for FlexDoc: {unit}")

    def size_summary(self) -> str:
        nbytes = self.size(TextUnit.bytes)
        if nbytes > 0:
            return (
                f"{nbytes} bytes ("
                f"{self.size(TextUnit.lines)} lines, "
                f"{self.size(TextUnit.paragraphs)} paras, "
                f"{self.size(TextUnit.sentences)} sents, "
                f"{self.size(TextUnit.words)} words, "
                # f"{self.size(TextUnit.wordtoks)} wordtoks, "
                f"~{self.size(TextUnit.tokens)} tok)"
            )
        else:
            return f"{nbytes} bytes"

    def as_wordtok_to_sent(
        self, bof_eof: bool = False
    ) -> Generator[tuple[str, SentIndex], None, None]:
        # An empty document has no sentences; boundary tokens map to a sentinel index so
        # `as_wordtoks(bof_eof=True)` yields just BOF/EOF instead of raising on last_index().
        if not self.paragraphs:
            if bof_eof:
                yield BOF_TOK, SentIndex(0, 0)
                yield EOF_TOK, SentIndex(0, 0)
            return

        if bof_eof:
            yield BOF_TOK, self.first_index()

        last_para_index = len(self.paragraphs) - 1
        for para_index, para in enumerate(self.paragraphs):
            for wordtok, sent_index in para.as_wordtok_to_sent():
                yield wordtok, SentIndex(para_index, sent_index)
            if para_index != last_para_index:
                yield PARA_BR_TOK, SentIndex(para_index, len(para.sentences) - 1)

        if bof_eof:
            yield EOF_TOK, self.last_index()

    def as_wordtoks(self, bof_eof: bool = False) -> Generator[str, None, None]:
        for wordtok, _sent_index in self.as_wordtok_to_sent(bof_eof=bof_eof):
            yield wordtok

    def wordtok_mappings(self) -> tuple[WordtokMapping, SentenceMapping]:
        """
        Get mappings between wordtok indexes and sentence indexes.
        """
        sent_indexes = [sent_index for _wordtok, sent_index in self.as_wordtok_to_sent()]

        wordtok_mapping = {i: sent_index for i, sent_index in enumerate(sent_indexes)}

        sent_mapping = defaultdict(list)
        for i, sent_index in enumerate(sent_indexes):
            sent_mapping[sent_index].append(i)

        return wordtok_mapping, sent_mapping

    def collect(
        self,
        *,
        subtree_of: str | None = None,
        within: str | tuple[int, int] | None = None,
        overlaps: str | tuple[int, int] | None = None,
        kinds: set[NodeKind] | None = None,
        where: Callable[[Node], bool] | None = None,
        recursive: bool = False,
        inline: bool = False,
        layer: set[Layer] | None = None,
    ) -> list[Node]:
        """
        Convenience that calls `collect()` over `self.node_table()`. See
        `flexdoc.docs.collect.collect` for parameter details.
        """
        return _collect(
            self.node_table(),
            subtree_of=subtree_of,
            within=within,
            overlaps=overlaps,
            kinds=kinds,
            where=where,
            recursive=recursive,
            inline=inline,
            layer=layer,
        )

    def graph(
        self,
        *,
        include: frozenset[Layer] | None = None,
        detail: frozenset[Detail] = frozenset(),  # pyright: ignore[reportCallInDefaultInitializer]
    ) -> DocGraph:
        """
        Build a `DocGraph` projection of this document. `include` selects which
        layers to serialize (default: markdown + document); `detail` controls
        payload richness (see `Detail`). See `flexdoc.docs.doc_graph` for the
        full contract.
        """
        effective_include = include if include is not None else DEFAULT_INCLUDE
        return build_doc_graph(self.node_table(), include=effective_include, detail=detail)

    @override
    def __str__(self):
        return f"FlexDoc({self.size_summary()})"
