"""
The blank-line editing view: `Paragraph` and `Sentence` units with exact source
offsets (`Offsets`, `SentIndex`), per-paragraph `BlockType` classification, and the
sentence-splitter hook. These are the units `FlexDoc` edits and reassembles; the
structural layer lives in `flexdoc.docs.block_tree`.
"""

from __future__ import annotations

from collections.abc import Callable, Generator, Iterable
from dataclasses import dataclass
from functools import cached_property
from typing import NamedTuple, TypeAlias

import regex
from flowmark import flowmark_markdown, split_sentences_regex
from flowmark.atomic_spans import split_sentences_with_spans
from funlog import tally_calls
from marko.block import BlankLine, Heading, SetextHeading
from typing_extensions import override

from flexdoc.docs.block_info import (
    CodeInfo,
    ListInfo,
    TableInfo,
    code_info_for,
    list_info_for,
    table_info_for,
)
from flexdoc.docs.block_types import BlockType, block_type_for
from flexdoc.docs.links import Link, block_links
from flexdoc.docs.sizes import TextUnit, size, size_in_bytes
from flexdoc.docs.wordtoks import (
    SENT_BR_STR,
    SENT_BR_TOK,
    is_break_or_space,
    is_header_tag,
    is_tag,
    is_word,
    wordtokenize,
)
from flexdoc.util.token_estimate import estimate_tokens

SYMBOL_PARA = "¶"

SYMBOL_SENT = "S"

FOOTNOTE_DEF_REGEX = regex.compile(r"^\[\^[^\]]+\]:")


Splitter: TypeAlias = Callable[[str], list[str]]

default_sentence_splitter: Splitter = split_sentences_regex
"""
The default sentence splitter. Can be replaced with a more advanced splitter like
Spacy. We default to the regex splitter because it's usable (in English), eliminates
the need for a dependency on Spacy, and is much faster than Spacy.
"""


def is_markdown_header(markdown: str) -> bool:
    """
    Is the start of this content a Markdown header?
    """
    return regex.match(r"^#+ ", markdown) is not None


class _BlockInfo(NamedTuple):
    """A paragraph's classification from one parse: its `BlockType` and, for headings,
    the level and title, plus typed code/table/list metadata for the matching kinds.
    Caches the small derived values, not the marko `Document`."""

    block_type: BlockType
    heading_level: int | None
    heading_title: str | None
    code_info: CodeInfo | None = None
    table_info: TableInfo | None = None
    list_info: ListInfo | None = None


def _inline_text(element: object) -> str:
    """Concatenate the plain text of an inline (or heading) element subtree."""
    children = getattr(element, "children", None)
    if isinstance(children, str):
        return children
    if isinstance(children, list):
        return "".join(_inline_text(child) for child in children)  # pyright: ignore[reportUnknownArgumentType]
    return ""


@dataclass(frozen=True, order=True)
class SentIndex:
    """
    Point to a sentence in a `FlexDoc`.
    """

    para_index: int
    sent_index: int

    @override
    def __str__(self):
        return f"{SYMBOL_PARA}{self.para_index},{SYMBOL_SENT}{self.sent_index}"


WordtokMapping: TypeAlias = dict[int, SentIndex]
"""A mapping from wordtok index to sentences in a FlexDoc."""

SentenceMapping: TypeAlias = dict[SentIndex, list[int]]
"""A mapping from sentence index to wordtoks in a FlexDoc."""


@dataclass(frozen=True)
class Offsets:
    """
    Character offsets of a parsed element, with the same shape for paragraphs,
    sentences, and any future parsed units.

    - `doc_offset`: absolute offset in the document.
    - `block_offset`: offset relative to the start of the enclosing block — the
      document for a paragraph (so it equals `doc_offset`), or the paragraph for a
      sentence.
    """

    doc_offset: int
    block_offset: int


@dataclass
class Sentence:
    """
    A sentence in a `FlexDoc`. `text` is the editable content (used by
    `reassemble()`); `offsets` is a fixed reference to the source set at parse time
    and is not updated by edits. Offsets are exact when the sentence is a verbatim
    slice of the paragraph (prose); for content where the splitter normalizes
    whitespace (e.g. tables), the offset is a best-effort position. See `FlexDoc`
    for the full contract.
    """

    text: str
    offsets: Offsets
    original_text: str | None = None

    @property
    def span(self) -> tuple[int, int]:
        """
        Absolute `[start, end)` character offsets of this sentence in the document.
        Exact when `original_text` (the verbatim source slice) is set — the default
        splitter sets it via flowmark's offset-preserving splitter, so
        `source_text[start:end] == original_text`. Falls back to `len(text)` for
        sentences produced by a custom (non-span-aware) splitter or by editing.
        """
        length = len(self.original_text if self.original_text is not None else self.text)
        return self.offsets.doc_offset, self.offsets.doc_offset + length

    def size(self, unit: TextUnit) -> int:
        return size(self.text, unit)

    def as_wordtoks(self) -> list[str]:
        return wordtokenize(self.text)

    def is_markup(self) -> bool:
        """
        Is this sentence all markup, e.g. a <span> or <div> tag or some other content with no words?
        """
        wordtoks = self.as_wordtoks()
        is_all_markup = all(is_tag(wordtok) or is_break_or_space(wordtok) for wordtok in wordtoks)
        if is_all_markup:
            return True
        is_markup_no_words = (
            len(wordtoks) > 2
            and is_tag(wordtoks[0])
            and is_tag(wordtoks[-1])
            and all(not is_word(wordtok) for wordtok in wordtoks[1:-1])
        )
        if is_markup_no_words:
            return True
        return False

    @override
    def __str__(self):
        return repr(self.text)


@dataclass
class Paragraph:
    """
    A paragraph (one blank-line-separated block) in a `FlexDoc`.

    `original_text` and `offsets` are fixed references to the source as parsed and
    are not updated by edits; `sentences` holds the editable content used by
    `reassemble()`. `block_type` is derived from `original_text` and cached, so it
    assumes `original_text` is not reassigned after construction. See `FlexDoc` for
    the full contract.
    """

    original_text: str
    sentences: list[Sentence]
    offsets: Offsets

    @property
    def end_offset(self) -> int:
        """Absolute end offset (exclusive) of this paragraph in the document."""
        return self.offsets.doc_offset + len(self.original_text)

    @property
    def span(self) -> tuple[int, int]:
        """
        Absolute `[start, end)` character offsets of this paragraph in the document,
        such that `source_text[start:end] == original_text`.
        """
        return self.offsets.doc_offset, self.end_offset

    @classmethod
    @tally_calls(level="warning", min_total_runtime=5)
    def from_text(
        cls,
        text: str,
        doc_offset: int = 0,
        sentence_splitter: Splitter = default_sentence_splitter,
    ) -> Paragraph:
        # TODO: Lazily compute sentences for better performance.
        sentences: list[Sentence] = []
        if sentence_splitter is default_sentence_splitter:
            # Default path: flowmark's offset-preserving, atomic-aware splitter gives
            # exact verbatim spans (never bisecting a link/code span). Keep
            # `Sentence.text` whitespace-normalized (as the regex splitter produced)
            # for backward-compatible wordtok/diff/reassemble behavior; `original_text`
            # holds the verbatim slice so `span` is exact.
            for sent_span in split_sentences_with_spans(text):
                normalized = " ".join(sent_span.text.split())
                sentences.append(
                    Sentence(
                        normalized,
                        Offsets(
                            doc_offset=doc_offset + sent_span.start, block_offset=sent_span.start
                        ),
                        original_text=sent_span.text,
                    )
                )
        else:
            # Custom splitter (returns plain strings): locate each sentence by search;
            # offsets are best-effort where the splitter normalized whitespace.
            cursor = 0
            for sent_str in sentence_splitter(text):
                idx = text.find(sent_str, cursor)
                if idx < 0:
                    idx = cursor
                sentences.append(
                    Sentence(sent_str, Offsets(doc_offset=doc_offset + idx, block_offset=idx))
                )
                cursor = idx + len(sent_str)
        return cls(
            original_text=text,
            sentences=sentences,
            offsets=Offsets(doc_offset=doc_offset, block_offset=doc_offset),
        )

    def reassemble(self) -> str:
        return SENT_BR_STR.join(sent.text for sent in self.sentences)

    def replace_str(self, old: str, new: str):
        for sent in self.sentences:
            sent.text = sent.text.replace(old, new)

    def sent_iter(self, reverse: bool = False) -> Iterable[tuple[int, Sentence]]:
        enum_sents = list(enumerate(self.sentences))
        return reversed(enum_sents) if reverse else enum_sents

    def size(self, unit: TextUnit) -> int:
        if unit == TextUnit.lines:
            return len(self.original_text.splitlines())
        if unit == TextUnit.paragraphs:
            return 1
        if unit == TextUnit.sentences:
            return len(self.sentences)

        if unit == TextUnit.tokens:
            return estimate_tokens(self.reassemble())

        base_size = sum(sent.size(unit) for sent in self.sentences)
        if unit == TextUnit.bytes:
            return base_size + (len(self.sentences) - 1) * size_in_bytes(SENT_BR_STR)
        if unit == TextUnit.chars:
            return base_size + (len(self.sentences) - 1) * len(SENT_BR_STR)
        if unit == TextUnit.words:
            return base_size
        if unit == TextUnit.wordtoks:
            return base_size + (len(self.sentences) - 1)

        raise ValueError(f"Unsupported unit for Paragraph: {unit}")

    def as_wordtok_to_sent(self) -> Generator[tuple[str, int], None, None]:
        last_sent_index = len(self.sentences) - 1
        for sent_index, sent in enumerate(self.sentences):
            for wordtok in sent.as_wordtoks():
                yield wordtok, sent_index
            if sent_index != last_sent_index:
                yield SENT_BR_TOK, sent_index

    def as_wordtoks(self) -> Generator[str, None, None]:
        for wordtok, _ in self.as_wordtok_to_sent():
            yield wordtok

    def is_markup(self) -> bool:
        """
        Is this paragraph all markup, e.g. a <div> tag as a paragraph by itself?
        """
        return all(sent.is_markup() for sent in self.sentences)

    def is_header(self) -> bool:
        """
        Is this paragraph a Markdown or HTML header tag?
        """
        first_wordtok = next(self.as_wordtoks(), None)
        is_html_header = first_wordtok and is_tag(first_wordtok) and is_header_tag(first_wordtok)
        return is_html_header or is_markdown_header(self.original_text)

    def is_footnote_def(self) -> bool:
        """
        Is this paragraph a Markdown footnote definition block (e.g. "[^id]: text")?
        """
        if len(self.sentences) == 0:
            return False
        initial_text = self.sentences[0].text
        return FOOTNOTE_DEF_REGEX.match(initial_text) is not None

    @cached_property
    def _block_info(self) -> _BlockInfo:
        """
        Classify this paragraph and extract heading level/title from a single parse of
        `original_text` (which does not change after parsing). Cached; the marko document
        is not retained. See `BlockType` for blank-line-splitting caveats.
        """
        text = self.original_text.strip()
        if not text:
            return _BlockInfo(BlockType.paragraph, None, None)
        parsed = flowmark_markdown().parse(text)
        element = next((el for el in parsed.children if not isinstance(el, BlankLine)), None)
        block_type = block_type_for(element) if element is not None else BlockType.paragraph
        # marko treats a single-line HTML tag as an inline-HTML paragraph rather than
        # an HTML block, so fall back to flexdoc's own markup check for those.
        if block_type == BlockType.paragraph and self.is_markup():
            block_type = BlockType.html
        code_info = code_info_for(element) if element is not None else None
        table_info = table_info_for(element) if element is not None else None
        list_info = list_info_for(element) if element is not None else None
        if isinstance(element, (Heading, SetextHeading)):
            return _BlockInfo(block_type, element.level, _inline_text(element).strip())
        return _BlockInfo(block_type, None, None, code_info, table_info, list_info)

    @property
    def block_type(self) -> BlockType:
        """This paragraph's Markdown block kind (see `_block_info`)."""
        return self._block_info.block_type

    @property
    def heading_level(self) -> int | None:
        """The Markdown heading level (1-6) if this block is a heading, else None."""
        return self._block_info.heading_level

    @property
    def heading_title(self) -> str | None:
        """The heading text without `#` markers if this block is a heading, else None."""
        return self._block_info.heading_title

    @property
    def code_info(self) -> CodeInfo | None:
        """
        Typed code metadata (`language`, `line_count`) if this paragraph is a code block,
        else `None`. Density caveat (as for `block_type`): this is the editing view, split
        on blank lines, so a fenced code block containing a blank line is several
        paragraphs; the density-invariant source of truth is `Block.code_info` from
        `FlexDoc.blocks()`.
        """
        return self._block_info.code_info

    @property
    def table_info(self) -> TableInfo | None:
        """
        Typed table metadata (`rows`, `cols`, `cells`, `alignments`) if this paragraph is
        a table, else `None`. Editing-view density caveat applies; see `code_info`.
        """
        return self._block_info.table_info

    @property
    def list_info(self) -> ListInfo | None:
        """
        Typed list metadata (`ordered`, `start`, `max_depth`, `item_count`) if this
        paragraph is a list, else `None`. Editing-view density caveat applies: a loose
        list is one paragraph per item, so the whole-list view is `Block.list_info` from
        `FlexDoc.blocks()`. See `code_info`.
        """
        return self._block_info.list_info

    def links(self) -> list[Link]:
        """Links in this block, in order (identity always; absolute span when recoverable)."""
        return block_links(self.original_text, self.offsets.doc_offset)
