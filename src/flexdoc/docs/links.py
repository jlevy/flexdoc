"""
The `Link` value type and link extraction over a text region.

Identity comes from flowmark's `extract_links` (reference links resolved) plus a walk for
images and reference definitions; exact spans are recovered by aligning identities with
flowmark's atomic spans (and `block_span` for reference definitions). Each `Link` carries
a `LinkForm` discriminator. See `block_links`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import NamedTuple

from flowmark import flowmark_markdown
from flowmark.atomic_spans import iter_atomic_spans
from flowmark.markdown_ast import block_span, extract_links, walk_elements
from marko import inline
from marko.block import Document, LinkRefDef

from flexdoc.docs.block_tree import parse_blocks, walk_blocks
from flexdoc.docs.block_types import BlockType


class LinkForm(StrEnum):
    """
    How a link-like construct is written in the source. `inline`, `reference`, `autolink`,
    and `bare_url` are navigable links (`TRUE_LINK_FORMS`); `image` is an image; and
    `reference_definition` is a `[id]: url` definition line, surfaced for completeness.
    """

    inline = "inline"
    reference = "reference"
    autolink = "autolink"
    bare_url = "bare_url"
    image = "image"
    reference_definition = "reference_definition"


TRUE_LINK_FORMS: frozenset[LinkForm] = frozenset(
    {LinkForm.inline, LinkForm.reference, LinkForm.autolink, LinkForm.bare_url}
)
"""The navigable-link forms `FlexDoc.links()` returns by default."""


@dataclass(frozen=True)
class Link:
    """
    A link-like construct found in a document. `text`, `url`, and `title` are the parsed
    identity (reference links resolved, autolinks and bare URLs included); for an image
    `text` is the alt text and for a reference definition `text` is the definition id.
    `span` is the construct's absolute `[start, end)` offsets in the source when they could
    be recovered (`None` only when the construct cannot be located). `link_form`
    discriminates how it was written (see `LinkForm`).
    """

    text: str
    url: str
    title: str | None
    span: tuple[int, int] | None
    link_form: LinkForm


def _inline_text(element: object) -> str:
    """Concatenate the plain text of an inline element subtree (e.g. an image's alt)."""
    children = getattr(element, "children", None)
    if isinstance(children, str):
        return children
    if isinstance(children, list):
        return "".join(_inline_text(child) for child in children)  # pyright: ignore[reportUnknownArgumentType]
    return ""


class _Span(NamedTuple):
    """A located atomic span with absolute offsets into the scanned text."""

    start: int
    end: int
    text: str


def _markdown_link_atomics(block_text: str, parsed: Document) -> list[_Span]:
    """The `markdown_link` atomic spans in `block_text`, scanned per leaf structural block so
    inline backtick/code-span pairing stays bounded to one block. A whole-text scan lets an
    unbalanced backtick run in one block pair across a later block and swallow a link there,
    flipping an inline `[t](u)` to the bare-url fallback; per-block scanning prevents that (the
    same scoping the node table uses for inline discovery). Offsets are absolute into
    `block_text`, and leaf blocks stay in document order so `block_links`' alignment holds."""
    spans: list[_Span] = []
    for block, _depth in walk_blocks(parse_blocks(block_text, parsed)):
        if block.children or block.type in (BlockType.code, BlockType.thematic_break):
            continue
        start, _end = block.span
        for sp in iter_atomic_spans(block_text[start : block.span[1]]):
            if sp.is_atomic and sp.name == "markdown_link":
                spans.append(_Span(start + sp.start, start + sp.end, sp.text))
    return spans


def block_links(block_text: str, doc_offset: int, *, parsed: Document | None = None) -> list[Link]:
    """
    All link-like constructs in a text region, in document order, each with a `LinkForm`:
    navigable links (`inline`/`reference`/`autolink`/`bare_url`), `image`s, and
    `reference_definition`s.

    Identity comes from `extract_links` (reference links resolved against definitions
    anywhere in the region) for navigable links, an AST walk for images, and marko's
    `LinkRefDef` block elements for definitions. Spans for navigable links are recovered
    by aligning, in document order, with the bracketed `markdown_link` atomic spans from
    `iter_atomic_spans`, then a forward literal search for autolinks and bare URLs;
    image spans align with the `!`-prefixed atomics; definition spans come straight from
    `block_span`. A forward character cursor advances past each located span so repeated
    URLs and no-span identities do not desync the next match.

    `parsed` is the marko parse of exactly this `block_text`; pass it to reuse a shared
    parse, else it is parsed here.
    """
    doc = parsed if parsed is not None else flowmark_markdown().parse(block_text)
    identities = extract_links(doc)

    # `markdown_link` atomics are the bracketed `[...]` constructs (images when preceded by
    # `!`, navigable links otherwise). The scan is bounded per leaf block so an unbalanced
    # backtick run cannot pair across a block boundary and swallow a later link (which would
    # flip an inline link to the bare-url fallback). Autolinks come through as `html_open_tag`
    # and bare URLs are not atomic, so both use the literal fallback below.
    markdown_atomics = _markdown_link_atomics(block_text, doc)
    link_spans = [sp for sp in markdown_atomics if not _preceded_by_bang(block_text, sp.start)]
    image_spans = [sp for sp in markdown_atomics if _preceded_by_bang(block_text, sp.start)]

    result: list[Link] = []

    used: set[int] = set()
    scan_start = 0
    char_cursor = 0
    for idn in identities:
        located: tuple[int, int] | None = None
        link_form = LinkForm.inline

        # Bracketed links: match the next unused `markdown_link` atomic by URL (inline)
        # or by link text (reference links, where the URL is in a separate definition).
        for j in range(scan_start, len(link_spans)):
            if j in used:
                continue
            sp = link_spans[j]
            if idn.url and idn.url in sp.text:
                located, link_form = (sp.start, sp.end), LinkForm.inline
            elif idn.text and idn.text in sp.text and sp.text.startswith("["):
                located, link_form = (sp.start, sp.end), LinkForm.reference
            else:
                continue
            used.add(j)
            scan_start = j + 1
            break

        # Autolinks / bare URLs: locate the verbatim URL forward from the cursor; include
        # the surrounding angle brackets when present (an autolink `<url>`).
        if located is None and idn.url:
            idx = block_text.find(idn.url, char_cursor)
            if idx >= 0:
                start, end = idx, idx + len(idn.url)
                if (
                    start > 0
                    and block_text[start - 1] == "<"
                    and end < len(block_text)
                    and block_text[end] == ">"
                ):
                    start, end, link_form = start - 1, end + 1, LinkForm.autolink
                else:
                    link_form = LinkForm.bare_url
                located = (start, end)

        if located is not None:
            char_cursor = max(char_cursor, located[1])
            span: tuple[int, int] | None = (doc_offset + located[0], doc_offset + located[1])
        else:
            span = None
        result.append(Link(idn.text, idn.url, idn.title, span, link_form))

    # Images: identities from the AST, spans from the `!`-prefixed atomics in document
    # order. The image span includes the leading `!` (the atomic starts at the `[`).
    img_used: set[int] = set()
    img_cursor = 0
    for element in walk_elements(doc):
        if not isinstance(element, inline.Image):
            continue
        alt = _inline_text(element)
        url = element.dest or ""
        img_span: tuple[int, int] | None = None
        for j in range(img_cursor, len(image_spans)):
            if j in img_used:
                continue
            sp = image_spans[j]
            if (url and url in sp.text) or (alt and alt in sp.text):
                img_used.add(j)
                img_cursor = j + 1
                img_span = (doc_offset + sp.start - 1, doc_offset + sp.end)
                break
        result.append(Link(alt, url, element.title, img_span, LinkForm.image))

    # Reference definitions: parser-authoritative from marko `LinkRefDef` block elements,
    # with spans from `block_span`. `text` carries the definition id.
    for element in walk_elements(doc):
        if not isinstance(element, LinkRefDef):
            continue
        s, e = block_span(element)
        # Trim to the structural block's whitespace-trimmed extent: marko's block span for a
        # reference definition includes the line's trailing newline, which would escape the
        # containing paragraph's (trimmed) span and leave the node unparented — so a
        # block-scoped `collect()` could not find it. Matches block_tree's span trimming.
        while e > s and block_text[e - 1].isspace():
            e -= 1
        while s < e and block_text[s].isspace():
            s += 1
        title = element.title.strip("\"'") if element.title else None
        result.append(
            Link(
                element.label or "",
                element.dest or "",
                title,
                (doc_offset + s, doc_offset + e),
                LinkForm.reference_definition,
            )
        )

    # Document order across all forms; no-span identities (unlocatable references) sort last.
    result.sort(key=lambda link: (link.span is None, link.span[0] if link.span else 0))
    return result


def _preceded_by_bang(text: str, start: int) -> bool:
    """Whether the character before `start` is `!` (marking a `markdown_link` atomic as an
    image `![...]`)."""
    return start > 0 and text[start - 1] == "!"
