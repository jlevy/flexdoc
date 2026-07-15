"""
`SpanRef`: a durable, source-canonical span reference type.

The quoted text (`exact` plus optional `prefix`/`suffix` context) is the
canonical durable anchor; the offsets (`start`/`end`) are a recomputable hint.
Resolution accepts an offset fast path only when `exact` and captured context match,
then falls back to quote search with prefix/suffix disambiguation. A context-free hint
cannot choose between duplicate quotes; callers should use `from_span()`/`from_node()`
so context is captured, drop offsets with `to_persisted()`, and resolve through the
instance methods on the root-exported `SpanRef`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal
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

    @classmethod
    def from_quote(
        cls,
        exact: str,
        source_text: str,
        *,
        prefix: str | None = None,
        suffix: str | None = None,
    ) -> SpanRef:
        """
        Resolve an external exact quote and return a positioned reference.
        Missing or ambiguous quotes fail visibly instead of selecting an occurrence.
        When no context is supplied, the resolved source context is captured.
        """
        candidate = cls(exact=exact, prefix=prefix, suffix=suffix)
        result = resolve(candidate, source_text)
        if result is None:
            raise ValueError("quote is missing or ambiguous in source_text")
        if prefix is None and suffix is None:
            return cls.from_span(source_text, *result)
        candidate.start, candidate.end = result
        return candidate

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

    def resolve(self, source_text: str) -> tuple[int, int] | None:
        """
        Resolve this reference against `source_text`, returning its offsets or `None`
        when the quote is missing or ambiguous.
        """
        return resolve(self, source_text)

    def resolve_and_update(self, source_text: str) -> tuple[int, int] | None:
        """
        Resolve this reference and update its position hint on success.
        """
        return resolve_and_update(self, source_text)


@dataclass(frozen=True)
class QuoteResolution:
    """Internal exact-quote outcome shared by SpanRef and TextRef."""

    status: Literal["resolved", "missing", "ambiguous"]
    method: Literal[
        "source_position",
        "context_position",
        "exact_quote",
        "context_quote",
        "none",
    ]
    span: tuple[int, int] | None = None
    candidates: tuple[tuple[int, int], ...] = ()


def resolve_quote_exact(
    exact: str,
    source_text: str,
    *,
    prefix: str | None = None,
    suffix: str | None = None,
    start: int | None = None,
    trust_position: bool = False,
) -> QuoteResolution:
    """
    Resolve exact quote evidence conservatively. `trust_position` is valid only when
    the caller has independently matched the source hash.
    """
    if not exact:
        return QuoteResolution("missing", "none")
    if start is not None:
        end = start + len(exact)
        position_matches = 0 <= start <= end <= len(source_text) and source_text[start:end] == exact
        if position_matches and trust_position:
            return QuoteResolution("resolved", "source_position", (start, end))
        candidate = SpanRef(
            exact=exact,
            prefix=prefix,
            suffix=suffix,
            start=start,
            end=end,
        )
        if (
            position_matches
            and (prefix or suffix)
            and _context_matches_at(candidate, source_text, start, end)
        ):
            return QuoteResolution("resolved", "context_position", (start, end))

    occurrences = _find_occurrences(exact, source_text)
    if not occurrences:
        return QuoteResolution("missing", "none")
    candidates = tuple((position, position + len(exact)) for position in occurrences)
    if len(candidates) == 1:
        return QuoteResolution("resolved", "exact_quote", candidates[0])

    best = _best_match(occurrences, exact, prefix, suffix, source_text)
    if best is not None:
        return QuoteResolution(
            "resolved",
            "context_quote",
            (best, best + len(exact)),
        )
    return QuoteResolution("ambiguous", "none", candidates=candidates)


def resolve(span_ref: SpanRef, source_text: str) -> tuple[int, int] | None:
    """
    Resolve a `SpanRef` against `source_text`, returning the `(start, end)`
    offsets or None if the span cannot be found or remains ambiguous. Pure: it
    does not mutate `span_ref` (use `span_ref.resolve_and_update()` to also write the
    offsets back).

    Fast path: if `start`/`end` and at least one non-empty context window are
    present, the text at those offsets matches `exact`, and the captured
    `prefix`/`suffix` matches the surrounding text there, return immediately.
    Requiring context keeps a stale hint from silently anchoring to a different
    duplicate of the quote after an edit; a context-free or context-mismatched
    hint falls through to the quote search.
    Otherwise, search the full text for `exact`, disambiguating with
    `prefix`/`suffix`. When the quote occurs more than once and the context
    does not single out one occurrence (no context, or a tied best score), the
    result is None rather than a guess; resolution failure is a visible value,
    never a silent wrong anchor (spec section 11).

    With neither a non-empty `prefix` nor `suffix`, offsets cannot disambiguate
    duplicate quotes. A unique quote still resolves through the search path.
    """
    start = (
        span_ref.start
        if span_ref.start is not None and span_ref.end == span_ref.start + len(span_ref.exact)
        else None
    )
    result = resolve_quote_exact(
        span_ref.exact,
        source_text,
        prefix=span_ref.prefix,
        suffix=span_ref.suffix,
        start=start,
    )
    return result.span


def _find_occurrences(exact: str, source_text: str) -> list[int]:
    occurrences: list[int] = []
    search_start = 0
    while True:
        position = source_text.find(exact, search_start)
        if position < 0:
            return occurrences
        occurrences.append(position)
        search_start = position + 1


def _context_matches_at(span_ref: SpanRef, source_text: str, start: int, end: int) -> bool:
    """
    True when every non-empty context window (`prefix`/`suffix`) matches the text
    around `[start, end)`. A missing or empty window cannot disqualify because it
    provides no evidence; a non-empty window must match exactly for an offset hint
    to be trusted.
    """
    if span_ref.prefix:
        pre_start = max(0, start - len(span_ref.prefix))
        if source_text[pre_start:start] != span_ref.prefix:
            return False
    if span_ref.suffix:
        suf_end = min(len(source_text), end + len(span_ref.suffix))
        if source_text[end:suf_end] != span_ref.suffix:
            return False
    return True


def resolve_and_update(span_ref: SpanRef, source_text: str) -> tuple[int, int] | None:
    """
    Resolve a `SpanRef` and, on success, write the recomputed offsets back into
    `span_ref.start`/`span_ref.end`. Refs with captured context can then use the
    fast path; context-free refs retain the offsets only as a position hint.
    Returns the `(start, end)` offsets or None. The mutating counterpart to `resolve()`.
    """
    result = resolve(span_ref, source_text)
    if result is not None:
        span_ref.start, span_ref.end = result
    return result


def resolve_batch(span_refs: Iterable[SpanRef], source_text: str) -> list[tuple[int, int] | None]:
    """
    Resolve several references with the same conservative contract as `resolve()`.
    The clear loop is intentional until representative batches justify an index.
    """
    return [resolve(span_ref, source_text) for span_ref in span_refs]


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
        if prefix:
            pre_start = max(0, idx - len(prefix))
            actual_prefix = source_text[pre_start:idx]
            if actual_prefix == prefix:
                score += 2
            elif actual_prefix and (
                prefix.endswith(actual_prefix) or actual_prefix.endswith(prefix)
            ):
                score += 1
        if suffix:
            end = idx + len(exact)
            suf_end = min(len(source_text), end + len(suffix))
            actual_suffix = source_text[end:suf_end]
            if actual_suffix == suffix:
                score += 2
            elif actual_suffix and (
                suffix.startswith(actual_suffix) or actual_suffix.startswith(suffix)
            ):
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
