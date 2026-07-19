# Senior Engineering Review: Native TextRef Integration (PR #20)

**Date:** 2026-07-19

**Scope:** [PR #20](https://github.com/jlevy/flexdoc/pull/20) at head `29688d1`
(`codex/native-textref-integration`, 41 files, +4681/−330 against `main` at `450e523`).
Reviewed with the full branch checked out: all four new/rewritten core modules read in
full (`text_ref.py`, `text_ref_context.py`, `text_annotations.py`, `span_ref.py`), the
`doc_graph.py` unification, the spec rewrite (§10–§11), plan and research docs, usage
docs, the example, schemas, and the five new test files. `make lint` clean and 399
tests pass locally; edge cases probed by hand (details in §6). Emphasis, per request:
the design of the TextRef format itself and how it is integrated so that annotations
and extractions always carry systematic text references.

**Prior review context:** a full senior review was posted on the PR at `f4fe3c4`;
commit `844298e` addressed it and `29688d1` then reshaped the contract
(`refactor!: unify DocGraph and TextRef contract`). §5 gives a per-finding disposition
of that earlier review; all of its findings are verifiably addressed or made moot by
the unification. This review covers the post-refactor state.

**Verdict: approve with nits.** The reference format is well designed: a small,
exhaustive kernel (locator + hash + selector) with evidence-based anchoring, typed
conservative resolution, and strict wire discipline. It is genuinely domain-neutral and
the library now uses it consistently for annotation, extraction grounding, and graph
serialization. No blockers and no High findings. One Medium design gap (evidence
weight for large spans, R1) deserves a documented answer before this becomes the
long-term interchange story; four Low findings are small code/docs fixes.

* * *

## 1. Design Assessment

### 1.1 The format kernel is right

`TextRef = DocRef + optional source_hash + optional selector` with exactly four target
kinds (whole document, span, point, section) is the correct minimal decomposition for a
cross-domain reference microformat:

- **Consumer-owned opaque `DocRef`** keeps the format free of any filesystem, URL, or
  repo policy, which is what lets the same shape serve repos, databases, CMSes, and
  agent pipelines. The refusal to canonicalize (`./a.md` ≠ `a.md`) is the right
  strictness and is now documented in `docs/usage.md`.
- **Quote evidence as the durable anchor, positions as hints** is the correct inversion
  of the naive offset-based design. Offsets alone die on the first edit; quotes plus
  immediate context survive it. Making the whole-document `source_hash` the *only*
  thing that upgrades a position to trusted evidence gives the format a crisp,
  checkable trust rule rather than a heuristic one.
- **The selector set is exhaustive without being clever.** Span covers every contiguous
  range; point covers insertions/bookmarks with an explicit `affinity` rule for who
  owns the boundary; section is the one structural selector that genuinely cannot be a
  span (interior edits must preserve identity); whole-document is selector absence.
  The spec's rule that new structural selector kinds must prove a real identity
  requirement (flexdoc-spec §11.2) is a good guard against selector sprawl.
- **Versioning and extensibility are disciplined:** a pinned `format: "textref/0.1"`
  literal, `extra="forbid"` everywhere, namespaced `owner:name` extension keys, and a
  URI projection that refuses what it cannot represent (extensions, oversize) instead
  of lossily projecting. Committed JSON Schemas are pinned by tests.

Compared to the obvious alternatives: this is effectively a disciplined subset of W3C
Web Annotation's TextQuoteSelector/TextPositionSelector composition, but with a far
sharper resolution contract (typed outcomes and an explicit evidence ladder, where Web
Annotation leaves resolution semantics to implementations), and without the RDF/JSON-LD
weight. Browser text fragments remain available as a one-way projection
(`SpanRef.to_text_fragment()`), correctly quarantined as a rendered-text adapter
(§11.8). Node-id/AST-path addressing was rightly rejected: ids are parse-local.

### 1.2 Resolution semantics are the strongest part

The three independent axes (document / source validation / selector) with a typed
result and explicit `candidates` are exactly what downstream applications need to build
UI and repair flows. The evidence ladder held up under adversarial probing (§6):

- A hash-less ref whose stale `start` pointed at the *wrong* duplicate of a repeated
  quote resolved to the correct occurrence via `context_quote` — the misleading hint
  was ignored because context did not corroborate it.
- The same quote with *no* context reported `ambiguous` with both candidate ranges
  rather than guessing.
- Duplicate `## Notes` headings under different parents disambiguated correctly through
  heading-anchor context plus structure, even with positions stripped and hash removed.
- Sub-8-char affinity context reported `missing` rather than anchoring on weak
  evidence (`_MIN_POINT_AFFINITY_CONTEXT`).
- Axes stayed independent: a wrong expected hash yielded
  `source_validation=mismatched` with `selector=resolved via context_position`.

"Resolution never chooses an arbitrary duplicate" is not just asserted in the spec; the
implementation and tests actually enforce it (`tests/docs/test_span_ref.py:186` pins
the stale-hint case).

### 1.3 Integration: the library now has one reference story

The integration achieves the stated goal — *any time the library hands you a locatable
value, there is a deterministic path to a portable reference*:

- `FlexDoc.references(document=...)` is the single binding surface; `for_target()`
  covers Paragraph, Sentence, Block, BaseBlock, Link, Node, Section, and raw spans, and
  the spec makes "every public value with a valid source span must map" an invariant
  (§13) with `test_reference_context_maps_public_locatable_values` pinning it.
- `DocGraph/v0.2` as the *single* graph contract, with required `document` +
  `source_hash`, is the right unification. Every `source_span` in a graph is now a
  reference basis rather than a dead offset, and the spec's four-step recipe for
  materializing a TextRef from a node (§10) makes the graph-to-TextRef path explicit.
  Deleting `DocGraphV2`/`build_doc_graph_v2` rather than carrying two models was the
  correct pre-1.0 call, and it retroactively resolves the typed-union problem from the
  prior review.
- Annotations are consumer-owned values passed *to* rendering/serialization, never
  `FlexDoc` state. The `AnnotationSet` sidecar hoists shared identity; embedding into a
  graph requires a non-null matching hash (closing the prior review's silent
  evidence-upgrade hole, with `test_docgraph_rejects_a_hashless_sidecar` pinning it).
- The snapshot contract is sound: `FlexDoc.source_text` never mutates (edits live in
  paragraphs/sentences until `reassemble()`), so the frozen `TextRefContext` with
  bind-time hash plus lazily cached line/section indexes cannot go stale. Values that
  no longer match the snapshot (synthetic sentences, foreign objects) fail construction
  visibly with `TextRefTargetError`.

The breaking changes (`graph(document=...)` required, `sha256` → `source_hash`) are
correctly gated as a 0.4.0 minor bump in the changelog, and the fix is mechanical for
callers.

### 1.4 Use-case coverage

Checked each workflow the format claims to serve against the implementation:

| Use case | Path | State |
| --- | --- | --- |
| Citation with provenance | `to_uri()` / JSON + `source_hash` | Works; URI unavailable for large spans (R1) |
| Extraction grounding | consumer `source_refs` field, `examples/textref_workflows.py` | Works; convention documented in spec §11.3 |
| Annotation sidecars | `AnnotationSet` JSON/YAML, strict round-trip | Works |
| Review/feedback rendering | `render_annotations()` merged windows + unresolved groups | Works, deterministic, golden-pinned |
| LLM context retrieval | `context()` / `render_context()` | Works, bounded, deterministic |
| Graph interchange | `DocGraph/v0.2` + embedded entries | Works |
| Insertion points / bookmarks | point selectors + affinity | Works |
| Section addressing | semantic section selectors | Works, survives interior edits |
| Suggested edits | TextRef target + consumer envelope (deferred) | Deliberately out of scope, spec'd in §11.7 |

Deliberate v0.1 exclusions (discontiguous ranges, multi-document sidecars, fuzzy
re-anchoring, rendered-text selectors) are all stated in the spec rather than silent,
which is what makes them acceptable.

* * *

## 2. Findings

No Blocker or High findings.

### R1 (Medium, design/docs): full-text `exact` evidence makes large-span refs heavy and silently loses the URI form

`for_span`/`for_target` store the complete selected text as `SpanSelector.exact`
(`src/flexdoc/docs/text_ref_context.py:112`). Probed: a 12.5k-char paragraph produces a
12.7 KB JSON TextRef, `to_uri()` raises (over the 8192 limit,
`src/flexdoc/docs/text_ref.py:313`), and rendering falls back to
`URI: unavailable (use structured TextRef)`. For the stated goal — *every extraction
carries a ref* — large extractions (chunks, long paragraphs, code blocks, table blocks)
are the norm, so the weight and the missing URI form land exactly on the primary use
case. Sections avoid this via heading anchors, but spans over arbitrary large ranges
have no bounded-evidence option, and embedding such annotations in a DocGraph
duplicates the full text per annotation.

This is a defensible v0.1 trade (full `exact` is maximally durable evidence), but it is
currently undocumented, and the natural mitigation is unspecified.

**Fix (pick one, both preferred):**

1. Document the trade now: a short paragraph in flexdoc-spec §11.4 and `docs/usage.md`
   stating that ref size is O(span length), the URI form is only for
   modest spans, and recommending section selectors for heading-owned regions and
   structured JSON (or graph embedding) for large spans.
2. Track a bounded-evidence span variant for a future format rev (e.g. head/tail
   context + length + span digest such as `exact_hash`), recorded in the research
   doc's open decisions so it shapes `textref/0.2` rather than being rediscovered.
   Resolution for such a selector composes cleanly with the existing ladder
   (boundary quotes behave like a two-sided point search plus length/digest check).

### R2 (Low, code): presentation line labels disagree with the canonical LF profile on non-LF separators

`_source_lines` uses `str.splitlines()`
(`src/flexdoc/docs/text_ref_context.py:502`), which also splits on `\f`, `\v`, `\x85`,
`U+2028`, `U+2029`. The canonical source profile normalizes only CRLF/CR and treats
those as content (flexdoc-spec §11.1). Probed: a document with a form feed and a
`U+2028` reports 5 display lines where the canonical profile (and any editor or
`wc -l`) sees 3, so `Range: L…` labels and window merging in rendered output disagree
with what a user sees in their editor for such documents. Display-only, but these
labels are explicitly meant as human-facing coordinates.

**Fix:** split on `"\n"` explicitly (iterate `source.split("\n")`, accumulating
offsets), keeping `SourceLine` construction otherwise identical; add one regression
test with `\f`/`U+2028` content.

### R3 (Low, code): `TextRefContext` equality/hash semantics are accidental

`TextRefContext` is `@dataclass(frozen=True)` over `_doc: FlexDoc`
(`src/flexdoc/docs/text_ref_context.py:88`). The generated members give it
value-equality that deep-compares the entire document (O(doc), probed `True` for two
separate binds) and a generated `__hash__` that raises at runtime
(`TypeError: unhashable type: 'FlexDoc'`, since `FlexDoc` is a mutable dataclass). A
frozen dataclass that advertises hashability but throws on `hash()` is a small trap
for consumers who key caches by context.

**Fix:** declare `@dataclass(frozen=True, eq=False)` so the context has identity
semantics (object hash, identity equality), which matches its role as a binder rather
than a value.

### R4 (Low, API): `SelectorStatus.unsupported` is overloaded for "wrong document"

Resolving a ref for a different document returns `document=invalid` with
`selector=unsupported` (`src/flexdoc/docs/text_ref.py:390`) — the same selector value
used for "section selector without structure". A consumer branching on `selector`
alone conflates the two, and `render_annotations` prints `Resolution: unsupported` for
entries in the Orphaned group (probed), where the operative fact is the document axis.
The axes are independent by design, so this is recoverable by checking `document`
first, but nothing tells a consumer they must.

**Fix (pick one):** have `_annotation_lines`/`_resolution_label` render the document
axis when `document != resolved` (e.g. `Resolution: document invalid`); and/or state in
flexdoc-spec §11.5 and the `TextRefResolution` docstring that `selector` is meaningful
only when `document == resolved`. A distinct `not_evaluated` status would be cleaner
but costs a format-visible enum value; the doc/render fix is enough for 0.1.

### R5 (Low, nit): hardcoded format literal

`AnnotationSet.expand()` constructs targets with `format="textref/0.1"`
(`src/flexdoc/docs/text_annotations.py:124`) instead of the imported `TEXTREF_FORMAT`
constant used elsewhere. **Fix:** use the constant.

* * *

## 3. Suggestions (non-blocking)

- **S1:** `_parse_position` accepts leading zeros (`start=0042` parses to 42, probed)
  and re-emits canonically; the codec is otherwise byte-strict in both directions.
  Rejecting non-canonical integers (`len(raw) > 1 and raw.startswith("0")`) would
  close the one asymmetry (`src/flexdoc/docs/text_ref.py:717`).
- **S2:** `DocGraph._validate_graph_references` bounds-checks node spans against
  embedded `source.text` but not embedded annotation `start`/`position` hints
  (`src/flexdoc/docs/doc_graph.py:142`); mirroring the check would extend the
  "produced only when it satisfies the schema" posture to annotations.
- **S3:** `docs/usage.md` still presents `SpanRef.to_persisted()` persistence with no
  pointer that TextRef is the portable form. One steering sentence ("persist TextRef
  for anything that leaves the process; SpanRef is in-memory machinery") would keep
  new consumers off the legacy persistence path while it remains supported for 0.4.
- **S4:** flexdoc-spec §11.1 states the canonical profile but not that Unicode
  normalization is *not* applied. Probed: an NFD quote misses an NFC source. Producers
  capturing evidence from anything other than the canonical bytes (rendered HTML,
  PDFs, other tools' output) will hit this; one warning sentence plus the existing
  future-fuzzy-tier note (§11.5) covers it.
- **S5:** A regression test that `render_context`/`render_annotations` fall back
  cleanly when `to_uri()` exceeds the length limit would pin the R1 fallback behavior
  (currently only exercised implicitly).

* * *

## 4. Verified benign (do not "fix")

- **Stale/misleading position hints cannot silently mis-anchor.** Hash-less positions
  are only honored when context corroborates them at that exact offset; otherwise
  resolution falls through to quote search and either disambiguates by context or
  reports `ambiguous` with candidates (probed both ways; pinned at
  `tests/docs/test_span_ref.py:186`).
- **Editing does not invalidate bound contexts.** `replace_str`/sentence edits change
  paragraphs, not `source_text`; refs made after editing still describe the parsed
  snapshot (probed: `exact` was the original text), which is the documented FlexDoc
  contract — re-parse to reference edited content.
- **Performance is fine.** On a 330 KB / 12k-paragraph document: `for_target` ~55 µs,
  hash-matched resolve ~45 µs, hash-less quote resolve ~60 µs, hash-less point resolve
  sub-ms (the prefix+suffix concat search), section resolve ~1 ms, `for_section` ~2 ms.
  An initially alarming 0.6 s measurement traced to `Section` tree traversal in the
  probe itself, outside this PR. Snapshot indexes are computed once per context
  (`cached_property`) and `resolve()` reuses the bind-time hash.
- **`_best_match` partial-credit scoring cannot prefer a spurious occurrence.** Partial
  scores only arise for boundary-truncated windows; ties refuse (return `None` →
  `ambiguous`), so weaker evidence never outvotes exact context.
- **Embedded annotation aliasing.** `DocGraph(annotations=...)` revalidates and copies
  the entry list; later sidecar mutation cannot reach into a built graph.
- **`boundary_mismatched` on a renamed *next* heading** is deliberate corroboration
  strictness, not a bug: the structurally derived span is still attached to the result
  for consumers whose policy accepts it.

* * *

## 5. Disposition of the prior review (at `f4fe3c4`)

| Prior finding | State at `29688d1` |
| --- | --- |
| 1. `graph()` union return breaks typed v0.1 consumers | **Moot** — single `DocGraph` model/builder; no union remains |
| 2. Hash-less sidecars silently upgraded via graph embedding | **Fixed** — `build_doc_graph` requires a matching non-null hash (`doc_graph.py:272`); regression tests added |
| 3. Point-context O(n) boundary scan | **Fixed** — prefix+suffix concatenation search (`text_ref.py:503`); probed sub-ms on large doc |
| 4. Per-call recomputation in `TextRefContext` | **Fixed** — `cached_property` indexes + `actual_source_hash` reuse; `test_reference_context_reuses_snapshot_indexes` pins it |
| 5. Context-free point rule unspecified | **Fixed** — normative in spec §11.2 and usage.md; URI rejection matches |
| Minor: `__all__`, truthiness on `boundary_start`, duplicated `_find_occurrences`, ambiguous-section test gap, `DocumentStatus.unavailable` note, DocRef opacity note | **All addressed** — complete `__all__`; `is not None` coalescing; single shared `find_occurrences`/`resolve_quote_exact` in `span_ref.py`; `test_section_resolution_reports_ambiguous_structural_matches`; both doc notes present in usage.md |

* * *

## 6. Validation performed

- `make lint` clean; `make test` 399 passed on the branch (including supply-chain
  checks).
- Ran `examples/textref_workflows.py` (also exercised by `test_examples.py`).
- Hand probes (all conservative behaviors confirmed): URI codec adversarial inputs
  (duplicate keys, empty values, raw `+`, bad percent escapes, unknown fields,
  invalid affinity, context-free positions) all rejected with clear errors;
  round-trip through hostile content (`&`, `=`, `%`, newlines, em-dash) exact;
  duplicate-quote and duplicate-heading disambiguation with and without hash and
  positions; document edges and empty documents; NFC/NFD mismatch; large-doc timing;
  graph embed → JSON → rehydrate → re-expand → resolve round trip; cross-document
  annotations grouped as Orphaned.
- CI at head `29688d1`: all 8 checks green (builds on 3.11–3.14 Linux + macOS 3.13,
  wheel-smoke, audit; Bugbot neutral — usage limit, did not run).

## 7. Documentation

Spec (§10–§11, §13–§14), usage.md, README, CHANGELOG (0.4.0 gating), TODO.md, the plan
spec, and the research doc are all updated in this PR and consistent with the
implementation — each doc claim I checked matched behavior. Doc deltas wanted: the R1
size guidance, R4 axis-precedence sentence, and suggestions S3/S4 above.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
