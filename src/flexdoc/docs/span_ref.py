"""
`SpanRef`: a durable, source-canonical span reference type.

The quoted text (`exact` plus optional `prefix`/`suffix` context) is the
canonical durable anchor; the offsets (`start`/`end`) are a recomputable hint.
Resolution accepts an offset fast path only when `exact` and any captured context
match, then falls back to quote search with prefix/suffix disambiguation.

Context-free refs are a deliberate boundary: an exact-matching offset is accepted
because no context can corroborate or reject it. Callers persisting a ref across edits
should use `from_span()`/`from_node()` so context is captured, or drop the offsets with
`to_persisted()`.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from flexdoc.docs.node import Node

# Default context window size for prefix/suffix capture.
_CONTEXT_WINDOW = 24


def _encode_fragment_part(text: str) -> str:
    """
    Percent-encode one component of a `#:~:text=` fragment. Encodes everything
    that is not unreserved, and additionally `-` and `,` (which are structural
    delimiters in the fragment grammar) so component text can never be mistaken
    for a `prefix-,` / `,-suffix` boundary.
    """
    return quote(text, safe="").replace("-", "%2D").replace(",", "%2C")


@dataclass
class SpanRef:
    """
    A span reference carrying two coordinated anchors: a quoted text span
    (canonical, durable) and character offsets (a recomputable hint).

    `exact` is the verbatim text of the referenced span. `prefix` and
    `suffix` are short context windows around it for disambiguation.
    `start` and `end` are Unicode code-point offsets into the source text.
    """

    exact: str
    prefix: str | None = None
    suffix: str | None = None
    start: int | None = None
    end: int | None = None

    @classmethod
    def from_node(cls, node: Node, source_text: str) -> SpanRef:
        """
        Build a `SpanRef` from a `Node` that has a `source_span`. Fills `exact`
        from the source text, captures prefix/suffix context, and sets offsets.
        """
        if node.source_span is None:
            raise ValueError(f"Node {node.id} has no source_span")
        start, end = node.source_span
        return cls.from_span(source_text, start, end)

    @classmethod
    def from_span(cls, source_text: str, start: int, end: int) -> SpanRef:
        """
        Build a `SpanRef` from a source text and explicit offsets.
        """
        exact = source_text[start:end]
        prefix_start = max(0, start - _CONTEXT_WINDOW)
        prefix = source_text[prefix_start:start] if prefix_start < start else None
        suffix_end = min(len(source_text), end + _CONTEXT_WINDOW)
        suffix = source_text[end:suffix_end] if end < suffix_end else None
        return cls(exact=exact, prefix=prefix, suffix=suffix, start=start, end=end)

    def to_persisted(self, *, include_position_hint: bool = False) -> SpanRef:
        """
        Return a copy suitable for persistence. The quote (`exact`/`prefix`/`suffix`)
        is the durable anchor; offsets are valid only within the exact source they
        were computed from, so by default they are dropped (`include_position_hint`
        keeps them as a fast-path hint when persisting alongside that same source).
        """
        return SpanRef(
            exact=self.exact,
            prefix=self.prefix,
            suffix=self.suffix,
            start=self.start if include_position_hint else None,
            end=self.end if include_position_hint else None,
        )

    def to_text_fragment(self) -> str:
        """
        Produce a `#:~:text=` URL text-fragment directive. Format:
        `#:~:text=[prefix-,]exact[,-suffix]`, with each component percent-encoded.

        Browsers match rendered page text, not Markdown source. This direct projection
        therefore works for visible prose; callers targeting rendered Markdown must
        supply a ref whose quote and context already use the rendered text.
        """
        parts: list[str] = []
        if self.prefix:
            parts.append(f"{_encode_fragment_part(self.prefix)}-,")
        parts.append(_encode_fragment_part(self.exact))
        if self.suffix:
            parts.append(f",-{_encode_fragment_part(self.suffix)}")
        return "#:~:text=" + "".join(parts)


def resolve(span_ref: SpanRef, source_text: str) -> tuple[int, int] | None:
    """
    Resolve a `SpanRef` against `source_text`, returning the `(start, end)`
    offsets or None if the span cannot be found or remains ambiguous. Pure: it
    does not mutate `span_ref` (use `resolve_and_update` to also write the
    offsets back).

    Fast path: if `start`/`end` are present, the text at those offsets matches
    `exact`, and any captured `prefix`/`suffix` also matches the surrounding
    text there, return immediately. The context check is what keeps a *stale*
    hint from silently anchoring to a different duplicate of the quote after an
    edit; a hint whose context disagrees falls through to the quote search.
    Otherwise, search the full text for `exact`, disambiguating with
    `prefix`/`suffix`. When the quote occurs more than once and the context
    does not single out one occurrence (no context, or a tied best score), the
    result is None rather than a guess; resolution failure is a visible value,
    never a silent wrong anchor (spec section 11).

    With neither `prefix` nor `suffix`, an exact-matching offset is trusted. Such a ref
    cannot detect that an edit moved its intended occurrence onto another duplicate;
    durable refs should capture context or omit the position hint.
    """
    # A zero-width quote anchors nothing; reject it on both paths.
    if not span_ref.exact:
        return None

    # Fast path: offsets are valid and any captured context corroborates them.
    if span_ref.start is not None and span_ref.end is not None:
        s, e = span_ref.start, span_ref.end
        if (
            0 <= s <= e <= len(source_text)
            and source_text[s:e] == span_ref.exact
            and _context_matches_at(span_ref, source_text, s, e)
        ):
            return (s, e)

    # Slow path: search for the exact text in the source.
    exact = span_ref.exact

    # Collect all occurrences.
    occurrences: list[int] = []
    search_start = 0
    while True:
        idx = source_text.find(exact, search_start)
        if idx < 0:
            break
        occurrences.append(idx)
        search_start = idx + 1

    if not occurrences:
        return None

    if len(occurrences) == 1:
        best = occurrences[0]
    else:
        # Disambiguate with prefix/suffix scoring; ambiguous stays unresolved.
        best_or_none = _best_match(
            occurrences, exact, span_ref.prefix, span_ref.suffix, source_text
        )
        if best_or_none is None:
            return None
        best = best_or_none

    return (best, best + len(exact))


def _context_matches_at(span_ref: SpanRef, source_text: str, start: int, end: int) -> bool:
    """
    True when every *captured* context window (`prefix`/`suffix`) matches the
    text around `[start, end)`. A `None` window cannot disqualify (no context
    was captured, e.g. at a document edge or on a hand-built ref); a present
    window must match exactly for an offset hint to be trusted.
    """
    if span_ref.prefix is not None:
        pre_start = max(0, start - len(span_ref.prefix))
        if source_text[pre_start:start] != span_ref.prefix:
            return False
    if span_ref.suffix is not None:
        suf_end = min(len(source_text), end + len(span_ref.suffix))
        if source_text[end:suf_end] != span_ref.suffix:
            return False
    return True


def resolve_and_update(span_ref: SpanRef, source_text: str) -> tuple[int, int] | None:
    """
    Resolve a `SpanRef` and, on success, write the recomputed offsets back into
    `span_ref.start`/`span_ref.end` so subsequent resolves hit the fast path.
    Returns the `(start, end)` offsets or None. The mutating counterpart to
    `resolve()`.
    """
    result = resolve(span_ref, source_text)
    if result is not None:
        span_ref.start, span_ref.end = result
    return result


def _best_match(
    occurrences: list[int],
    exact: str,
    prefix: str | None,
    suffix: str | None,
    source_text: str,
) -> int | None:
    """
    Among multiple occurrences of `exact`, pick the one best matching the
    prefix/suffix context. Returns the start offset of the unique best match,
    or None when no occurrence scores strictly better than the rest (no
    context to score with, or a tie); the caller treats that as ambiguous.
    """
    best_idx: int | None = None
    best_score = -1
    tied = False
    for idx in occurrences:
        score = 0
        if prefix is not None:
            pre_start = max(0, idx - len(prefix))
            actual_prefix = source_text[pre_start:idx]
            if actual_prefix == prefix:
                score += 2
            elif prefix.endswith(actual_prefix) or actual_prefix.endswith(prefix):
                score += 1
        if suffix is not None:
            end = idx + len(exact)
            suf_end = min(len(source_text), end + len(suffix))
            actual_suffix = source_text[end:suf_end]
            if actual_suffix == suffix:
                score += 2
            elif suffix.startswith(actual_suffix) or actual_suffix.startswith(suffix):
                score += 1
        if score > best_score:
            best_score = score
            best_idx = idx
            tied = False
        elif score == best_score:
            tied = True
    if tied or best_score <= 0:
        return None
    return best_idx
