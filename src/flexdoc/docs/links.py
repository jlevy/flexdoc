"""
The `Link` value type and link extraction over a text region.

Identity comes from flowmark's `extract_links` (reference links resolved); exact
spans are recovered by aligning identities with flowmark's atomic spans plus a
literal forward search for autolinks and bare URLs. See `block_links`.
"""

from __future__ import annotations

from dataclasses import dataclass

from flowmark import flowmark_markdown
from flowmark.atomic_spans import iter_atomic_spans
from flowmark.markdown_ast import extract_links
from marko.block import Document


@dataclass(frozen=True)
class Link:
    """
    A link found in a document. `text`, `url`, and `title` are the parsed identity
    (reference links resolved, autolinks and bare URLs included), via flowmark's
    `markdown_ast.extract_links`. `span` is the link's absolute `[start, end)` offsets in
    the source when they could be recovered: inline links, autolinks (`<url>`), bare URLs,
    and reference links whose bracketed use is locatable all get a span. `span` is `None`
    only when the construct cannot be located in the source.
    """

    text: str
    url: str
    title: str | None
    span: tuple[int, int] | None


def block_links(block_text: str, doc_offset: int, *, parsed: Document | None = None) -> list[Link]:
    """
    Links in a text region. Identity comes from `extract_links` (always correct,
    including reference links resolved against definitions anywhere in the region);
    spans are recovered by aligning, in document order, with the bracketed link atomic
    spans from `iter_atomic_spans` (`markdown_link`), then a forward literal search for
    autolinks and bare URLs (which flowmark does not emit as link atomics). Identities
    that still cannot be located keep their identity but get `span=None`.

    A forward character cursor (`char_cursor`) advances past each located span so that
    bracketed matches, autolinks, bare URLs, and repeated URLs resolve in document order
    without one no-span identity desyncing the next.

    `parsed` is the marko parse of `block_text`; pass it to reuse a shared parse (the
    caller guarantees it is the parse of exactly this `block_text`), else it is parsed
    here.
    """
    identities = extract_links(
        parsed if parsed is not None else flowmark_markdown().parse(block_text)
    )
    # Only `markdown_link` atomics are bracketed `[...]` link constructs; autolinks come
    # through as `html_open_tag` and bare URLs are not atomic, so both are handled by the
    # literal fallback below.
    link_spans = [
        span
        for span in iter_atomic_spans(block_text)
        if span.is_atomic and span.name == "markdown_link"
    ]
    used: set[int] = set()
    result: list[Link] = []
    scan_start = 0
    char_cursor = 0
    for idn in identities:
        located: tuple[int, int] | None = None

        # Bracketed links: match the next unused `markdown_link` atomic by URL (inline)
        # or by link text (reference links, where the URL is in a separate definition).
        for j in range(scan_start, len(link_spans)):
            if j in used:
                continue
            sp = link_spans[j]
            if (idn.url and idn.url in sp.text) or (
                idn.text and idn.text in sp.text and sp.text.startswith("[")
            ):
                located = (sp.start, sp.end)
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
                    start, end = start - 1, end + 1
                located = (start, end)

        if located is not None:
            char_cursor = max(char_cursor, located[1])
            result.append(
                Link(
                    idn.text, idn.url, idn.title, (doc_offset + located[0], doc_offset + located[1])
                )
            )
        else:
            result.append(Link(idn.text, idn.url, idn.title, None))
    return result
