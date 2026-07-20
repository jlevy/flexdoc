# Senior Engineering Review: FlexDoc v0.4.0 Release Candidate (2026-07)

**Date:** 2026-07-20

**Scope:** PR #21 (`codex/release-readiness-textref`, head `739e503`) and the complete
`v0.3.0..HEAD` span it gates for release: five commits and 68 changed files covering
TextRef models, codecs, and exact resolution
([`text_ref.py`](../../../src/flexdoc/docs/text_ref.py)), document-bound construction
and rendering ([`text_ref_context.py`](../../../src/flexdoc/docs/text_ref_context.py)),
annotations ([`text_annotations.py`](../../../src/flexdoc/docs/text_annotations.py)),
DocGraph v0.2 ([`doc_graph.py`](../../../src/flexdoc/docs/doc_graph.py)), logical word
metrics (`flexdoc.util`), public exports, schemas, documentation, and packaging.
Builds on
[`senior-engineering-review-flexdoc-2026-07.md`](senior-engineering-review-flexdoc-2026-07.md).

**Review mode:** independent line-level read of the fix commit and every module it
touches; API surface diff against the `v0.3.0` tag; full local validation plus
adversarial edge probes beyond the suite; verification of the PR's validation claims
where this repository allows it. Tracked as bead `flexdoc-4jx1`.

* * *

## 1. Verdict

The candidate is ready to release as **v0.4.0** once the one open coordination item
(§6) is settled. All three fixes in PR #21 are correct, they tighten contracts that
have never shipped in a release (so they break no released consumer), and every
validation gate passes. This review branch adds documentation fixes only (§5); no code
changes were needed.

## 2. Validation Evidence

All commands ran on the PR head in a fresh checkout:

- `make lint`: codespell, Ruff check, Ruff format (no changes), and BasedPyright all
  clean; 0 errors, 0 warnings.
- `make test`: 407 passed.
- `uv run --group audit pip-audit`: no known vulnerabilities (the local `flexdoc` dev
  build itself is skipped, as expected).
- Tag-derived wheel (publishing runbook step 7): an isolated clone with a local-only
  `v0.4.0` tag builds `flexdoc-0.4.0-py3-none-any.whl` with `Version: 0.4.0` metadata
  and packages `py.typed`, `doc_graph_schema.json`, and `text_ref_schema.json`.
- Isolated-venv smoke of that wheel: parse, span/point/section references, URI
  round-trip, exact resolution, annotation-sidecar YAML round-trip, DocGraph v0.2
  embedding and JSON round-trip, logical and raw word counts, and packaged-schema
  loading all pass.
- PR CI: 7 of 7 required jobs green (Ubuntu on Python 3.11-3.14, macOS on 3.13,
  `audit`, `wheel-smoke`).
- Edge probes beyond the suite: a hash-bound `position=0` bare point is accepted; a
  hashless exact-less span is rejected; a bare mid-document point is rejected at YAML
  parse time; spans and points ending exactly at `len(source)` embed in a DocGraph
  while one past the end is rejected; `TextRefResolution.resolved` is false for every
  non-resolved document status.

Not verifiable from this repository: the PR's downstream suite runs (chopdiff 44,
practical-prose 49, kash 223, kash-docs 50, kash-media 1). Those are claims from the
PR author's environment; nothing in this review contradicts them.

## 3. PR #21 Fix Assessment

Three production changes, all correct:

- **`AnnotationSet` validates every entry through the complete TextRef contract.**
  `_validate_set` now constructs a `TextRef` per entry from the hoisted
  document/source-hash identity, so the TextRef evidence rules are enforced by the type
  that owns them rather than re-implemented. An invalid sidecar (for example a bare
  point at a nonzero position) now fails at construction and YAML parse time instead of
  later inside `expand()`. The prior narrower span rule is subsumed, and the
  spec (§11.2, §11.7) already required exactly this.
- **`build_doc_graph` bounds-checks embedded annotation positions.** The DocGraph model
  can only validate annotation bounds when `source.text` is embedded (`Detail.text`);
  default builds omit the text, so the builder now validates against the in-memory
  source before constructing the graph. A graph deserialized without source text still
  cannot bounds-check positions; that is inherent to omitting the text, and positions
  remain hints that resolution re-verifies against real source.
- **`TextRefResolution.resolved` honors its documented precondition.** Library-produced
  resolutions already coupled a non-resolved document with `SelectorStatus.unsupported`,
  so this hardens hand-constructed values rather than changing library behavior.

## 4. Breaking Changes v0.3.0 to v0.4.0 (Release-Notes Reference)

The candidate is intentionally not additive; per the pre-1.0 policy, breaking changes
bump the minor version. This section catalogs every incompatibility with its migration
and rationale, for reuse in the GitHub release notes.

### 4.1 `FlexDoc.graph()` Requires a Document Locator

`FlexDoc.graph()`, `build_doc_graph()`, and the debug helpers `doc_graph_yaml()` and
`dump_views()` now require a `document=` argument (a string or `DocRef`); `graph()`
also accepts optional `annotations=`.

- **Migration:** `doc.graph()` becomes `doc.graph(document="path/or/id.md")`.
- **Rationale:** every serialized graph now carries consumer-owned document identity
  plus a source hash, so TextRefs and annotation sidecars can be correlated with a
  graph without out-of-band context. FlexDoc validates the locator but never interprets
  it; retrieval stays consumer-owned.

### 4.2 DocGraph Wire Contract: v0.1 to v0.2

`schema` is now the literal `"DocGraph/v0.2"`. `source` carries required `document` and
algorithm-qualified `source_hash` (`sha256:<64 hex>`, shared with TextRef); the
unqualified `source.sha256` field is gone. All DocGraph models are strict: unknown
fields are rejected, types are strict, instances are frozen, and graph-level validation
enforces unique node ids, no dangling parent/child/view references, span/text
consistency when source text is embedded, and annotation bounds. An optional
`annotations` array embeds sidecar entries after the set's document and hash are
verified against the snapshot.

- **Migration:** consumers reading v0.1 JSON switch `source.sha256` to
  `source.source_hash` (now prefixed with `sha256:`) and read the new
  `source.document`; producers of graph JSON must drop unknown fields. Pinned golden
  outputs regenerate.
- **Rationale:** a derived snapshot format is most useful when it is self-identifying
  and rejects malformed data loudly; schema evolution happens by version bump rather
  than lenient parsing. (The changelog previously described this as removing
  `DocGraphV2`/`build_doc_graph_v2`; those names only ever existed inside PR #20's
  development history, never in a release, so the changelog now describes the change
  relative to v0.3.0.)

### 4.3 `TextUnit.words` Measures Logical Words

`TextUnit.words` is now a normalized logical-word measure; `TextUnit.raw_words` is the
literal whitespace-delimited count (the old `words` behavior). There is deliberately no
third `logical_words` alias. The change ripples through `size()`, `Paragraph.size()`,
`Sentence.size()`, `size_summary()`, `section_size_tree()` defaults, and debug-report
`words` fields. Counts match raw counts for ordinary non-wide prose averaging 3-6
characters per word; wide/fullwidth scripts, long identifiers and URLs, short-token
runs, and punctuation-dense content differ. Whole-text measures round once after
measuring, so sentence-by-sentence accumulation can differ slightly from a
whole-document count.

- **Migration:** callers needing the exact previous numbers use `TextUnit.raw_words`
  or `raw_word_count()`; everyone else keeps `TextUnit.words` and accepts better
  cross-language numbers.
- **Rationale:** a single `words` unit should mean "word-equivalent volume" across
  languages and formats. See the
  [logical-word definition and validation](https://gist.github.com/jlevy/0d6d87885f6d85f31440e58b8cfce663).

### 4.4 Token Estimation Scales Logical Words

`estimate_tokens(text, tokens_per_logical_word=TOKENS_PER_LOGICAL_WORD)` replaces the
`chars_per_token` parameter, and `TOKENS_PER_LOGICAL_WORD` (1.6, calibrated for
o200k-family tokenizers) replaces `CHARS_PER_TOKEN`. Estimates change numerically even
at defaults, and non-finite or non-positive factors now raise.

- **Migration:** drop or rename the keyword argument; recalibrate any hard-coded
  factor against the target model family.
- **Rationale:** characters-per-token breaks down across scripts and dense markup;
  logical words are the more stable base for a dependency-free estimate. Exact budgets
  still require the provider's tokenizer.

### 4.5 Reading Time Takes Logical Word Counts

`format_read_time()` keeps its signature but is now documented and calibrated for
logical word counts; the default rate corresponds to roughly 450 CJK characters per
minute under the default wide-character weight.

- **Migration:** pass `TextUnit.words` counts; behavior for plain English prose is
  effectively unchanged.

### 4.6 Golden and Snapshot Consumers

Any pinned DocGraph output changes: the `schema` value, the `source` block, and
logical-word `words` fields in reports. Regenerate goldens after upgrading.

### Additive Context (Not Breaking)

The TextRef surface is new: `TextRef`, `DocRef`, selectors, `TextRefResolution`,
`resolve_text_ref`, `normalize_source`, `source_hash`, `FlexDoc.references()` with
`TextRefContext` (construction, resolution, context windows, deterministic rendering),
`TextAnnotation`/`AnnotationSet`, DocGraph annotation embedding, committed JSON schemas
for both formats, `SpanRef.from_quote()`, promoted `resolve_batch`, and
`logical_word_count`/`raw_word_count` with their tuning constants. The root package now
exports the working set of these names; `tests/test_root_api.py` pins the surface.

## 5. Documentation Fixes Applied in This Review

- **CHANGELOG:** the DocGraph entry described removing `DocGraphV2` and
  `build_doc_graph_v2`, names that never shipped in any release; reworded to describe
  the v0.1-to-v0.2 contract change relative to v0.3.0 (§4.2 above).
- **TODO.md:** the logical-word-metrics item still sat under Open Work although PR #18
  shipped it and PR #21 marks its plan spec Implemented; removed.
- **flexdoc-spec.md §11.7:** the sidecar validity sentence named only the
  exact-less-span rule; it now states the full-contract invariant PR #21 enforces
  (every entry must satisfy the complete TextRef evidence contract under the hoisted
  identity).
- **README:** reworked per maintainer request: a compact example that shows the
  serialized formats working (TextRef URI, annotation sidecar YAML, DocGraph v0.2
  YAML) with real captured output, subsection headers, direct links to the key
  components and spec sections, and a status line reflecting 0.4.x.
- **Specs archive (`flexdoc-9z3m`, first half):** the seven implemented or superseded
  plans moved from `docs/project/specs/active/` to `docs/project/specs/done/`, with
  every cross-reference updated (and one dead link to a never-committed plan file
  de-linked). The extraction plan, the unified-document-model plan (Phases 3-4
  deferred), and the stabilization roadmap remain active; the roadmap-close half of
  `flexdoc-9z3m` stays open pending the Phase 2 and 3 gates.

## 6. Remaining Before the Tag

- **Downstream pins (`flexdoc-0e6q`, open):** `kash`, `kash-docs`, and `kash-media`
  depend on unbounded `flexdoc>=0.3.0`, so the v0.4.0 tag changes their resolved
  version. They should explicitly accept v0.4 semantics (notably §4.3 and §4.4) or add
  `<0.4` before the tag is cut. Their suites reportedly pass against this candidate.
- **At release time:** retitle the changelog `Unreleased` section to `0.4.0` with the
  release date, and cut the release per `docs/publishing.md`: either the maintainer
  `gh release create v0.4.0` path or the remote-agent path (update
  `.github/release-request/request.json` and `notes.md` on `main`). This review
  intentionally leaves the release-request files at v0.3.0 because landing a new tag
  there on `main` is what triggers the release.

## 7. Design Cleanliness Assessment

The v0.4 design was reviewed against its stated rationales; it is coherent and no
design changes are requested. The decisions that carry the release:

- **One reference composition.** `TextRef = DocRef + optional source_hash + optional
  selector`, with four exhaustive target kinds and consumer-owned retrieval. Identity
  questions (where) stay separate from annotation bodies and edits (what), which keeps
  every downstream schema consumer-owned.
- **Evidence-tier resolution that never guesses.** Positions are trusted only under a
  matched hash; otherwise quotes and context corroborate, and duplicates yield typed
  `ambiguous`/`missing` outcomes with candidates instead of a silent first match. This
  extends the SpanRef posture (spec §11) uniformly, including the
  8-character minimum for one-sided point affinity recovery.
- **Independent failure axes.** Document, source validation, and selector status are
  separate enums; PR #21 makes the `resolved` convenience respect the axis ordering the
  spec documents. Renderers group non-resolved documents as orphaned rather than
  misreporting selector status.
- **The point-zero sentinel.** A context-free point is valid only as hash-bound
  `position=0`: any other context-free point would become permanently unrecoverable the
  moment its snapshot changes, while document-start needs no evidence. All
  library-constructed points capture context; the rule constrains hand-built data.
- **Sidecar hoisting with single-source validation.** `AnnotationSet` hoists shared
  identity for concision, and validity is defined by literally constructing the
  expanded `TextRef` per entry, so the sidecar can never accept what expansion would
  reject.
- **Strict, versioned wire contracts.** DocGraph and TextRef models forbid unknown
  fields and pin exact format literals, with committed JSON Schemas and schema-sync
  tests. Evolution is explicit by version bump; the cost (older strict consumers reject
  newer producers) is the intended interop posture for a derived snapshot format.
- **Logical words without aliases.** Redefining `words` and adding `raw_words` avoids a
  permanent three-name unit vocabulary; the estimator scales words rather than
  characters. A documented, bounded normalization keeps the measure reproducible
  cross-language.

Accepted costs, documented in spec and docstrings: quote-anchored URI size is O(span
length) with an 8 KiB URI cap (structured JSON is the fallback); `extensions` are not
URI-projectable; ownership checks and `resolve_batch` scan linearly until profiling
justifies indexes.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
