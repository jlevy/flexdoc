# Senior Engineering Review: FlexDoc Pre-Promotion (2026-07)

**Date:** 2026-07-08

**Scope:** the whole repository at v0.2.0+—all of `src/flexdoc/`, the design of record
([`docs/flexdoc-spec.md`](../../flexdoc-spec.md)), user docs and README, the test suite
and golden corpus, packaging/CI, and fit for the AI document workflows the maintainer
wants to describe publicly (commenting/annotation, review feedback, chunking, grounded
citation). Builds on the 2026-06 standalone review
([`senior-engineering-review-flexdoc-standalone-2026-06.md`](senior-engineering-review-flexdoc-standalone-2026-06.md));
findings settled there were re-verified only where regression was possible.

**Review mode:** nine independent review passes (spec↔code consistency, docs accuracy,
API ergonomics, core-parse correctness, query/serialize/anchor correctness, tests and
goldens, packaging/release, AI-workflow fit, fresh-eyes adoption), each concrete finding
then adversarially verified against the source with runnable reproductions, plus a
completeness pass over what the nine missed.
Four findings were refuted in verification and are omitted or noted in §7. `make lint`
was clean and 338 tests passed before and after the initial fixes.
Follow-up review on 2026-07-09 added shared-parse and repeated-frontmatter-URL
regressions; 343 tests now pass.

**Context:** the maintainer intends to promote the library publicly and to describe its
value for AI/LLM document workflows.
The bar: polished docs, no known silent-corruption bugs, and a clear map of the design
decisions still open.

* * *

## 1. Executive Verdict

The model remains the right shape and the 2026-06 conclusions hold: one normalized
source string and one code-point offset space as the canonical substrate, sibling
projections over one shared parse, and quote-canonical references.

The initial round found two silent-corruption bugs and one `SpanRef` spec/code
divergence. Follow-up review found one remaining violation of the single-shared-parse
contract for frontmatter documents; all four are fixed in this branch (§2). The open
work is a pre-1.0 API decision batch (§5), release gates (§4), and mechanisms needed to
make the AI annotation/feedback story concrete rather than implied (§6).

**Recommended stance:** complete the 0.3.0 stabilization and release gates
(`flexdoc-r634`) before promotion.
Then implement the source-grounded AI workflow stage (`flexdoc-6582`) before presenting
annotation workflows as a released capability.
The staged plan is
[`plan-2026-07-09-flexdoc-stabilization-roadmap.md`](../specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md).

## 2. Correctness Fixes Applied in This Pass (Review the Decisions)

Three behavior changes were applied.
Each aligns the code with the spec’s stated posture, but each embeds a design decision
the maintainer should consciously ratify.
All are recorded in `CHANGELOG.md` under Unreleased.

### 2.1 CRLF input corrupted every structural view (P1, fixed by normalizing at parse)

marko computes block positions against LF-normalized text, but flexdoc indexed those
offsets into the original CRLF `source_text`. Each `\r\n` produced one character of
cumulative drift: on a small CRLF document, `blocks()` returned truncated spans
(`'Paragraph t'` for `'Paragraph two.'`), the base-block cover invariant (P13) was
violated, and `sections()`, `links()`, `prose_text()`, and the node table were all
garbled. The editing view was unaffected (its regex runs on the original text), which
made the corruption silent: `paragraphs` looked fine while the structural layer lied.
The spec claimed CRLF was “tolerated” (§4.5); that held only for the textual layer.
No CRLF document existed in the golden corpus, which is why the original 338-test suite
did not expose the defect.

**Fix chosen:** `from_text` now normalizes `\r\n` and lone `\r` to `\n` and retains the
normalized string as `source_text` (spec §4.1/§4.5 updated;
`tests/docs/test_line_endings.py` pins blocks/sections/base-block-cover/prose under CRLF
and lone-CR input).

**The decision embedded:** `source_text` is no longer byte-identical to a CRLF input;
offsets index the normalized text.
The alternative, remapping marko’s offsets back to original-CRLF coordinates, preserves
byte fidelity but adds a permanent coordinate-translation layer that every future span
producer must respect (and external annotators over the *file on disk* would still need
to know the mapping).
Normalization keeps “one offset space” literally true.
If byte-exact CRLF round-tripping ever matters (e.g. an editor bridge over unsaved CRLF
buffers), revisit with an explicit offset-mapping layer; do not partially un-normalize.

### 2.2 Markdown inside frontmatter could swallow the document body (P2, fixed)

The shared marko parse included the frontmatter region, so a YAML block scalar
containing a code fence
(`` ``` ``) opened a fenced block spanning the rest of the document. `_block_list` then dropped the frontmatter-owned block, leaving `blocks()`, `sections()`, `base_blocks()`, and `prose_text()`
empty for a document whose editing view was intact.

`_parsed()` now blanks non-newline frontmatter characters before parsing.
This preserves body offsets and prevents frontmatter from contributing blocks.
Follow-up review found that `_link_list()` still reparsed the body separately when
frontmatter was present; that path now passes the blanked source and shared parse to
`block_links()`. This also prevents a bare URL in frontmatter from stealing the span of
identical body URL text.
Regression coverage in `test_frontmatter_markdown_constructs_cannot_leak_into_body`,
`test_frontmatter_links_and_blocks_share_one_parse`, and the repeated-URL regression
verifies correctness and the single-parse contract.

### 2.3 `resolve()` guessed on ambiguous quotes (spec/code divergence, fixed toward the spec)

Spec §11: *“`resolve()` returns None when the quote is absent from the source or remains
ambiguous after prefix/suffix disambiguation.”* The implementation instead returned the
**first occurrence** whenever the quote appeared multiple times with no context, or with
context that matched no occurrence, or with a tied score—a silent wrong anchor, exactly
what the error posture (“visible, never silent” degradation) forbids.
For annotation workflows this is the difference between a trustworthy anchor and a
plausible-looking bug.

**Fix chosen:** multiple occurrences now resolve only when context singles out a unique
best match; no context, no corroborating context, or a tie returns `None`. Zero-width
quotes (`exact=""`) return `None` on both paths (previously the offset fast path
accepted them). Note the consequence: callers that relied on first-occurrence behavior
must now supply prefix/suffix (which `SpanRef.from_span` always captures).
If insertion-point references (empty `exact` at a position) are ever needed for the
annotation layer, that is a deliberate schema extension, not the old accident.

**Remaining boundary:** a hand-built `SpanRef` with offsets but no prefix or suffix
still trusts an exact-matching hint.
After an edit, that hint can land on a different duplicate and silently misanchor
because no context or source identity can reject it.
Library-built refs capture context and persisted refs drop offsets by default, so the
risk is bounded but real.
The 0.3.0 plan requires a decision between returning `None` for uncorroborated
duplicates and adding source identity (`flexdoc-qire`).

### 2.4 Smaller hardening (uncontroversial)

- `collect(overlaps=...)`: an empty `[x, x)` region or span now overlaps nothing
  (half-open semantics); point queries use `(x, x + 1)`.
- `render_node_attrs` attribute-escapes `node.id`; `wrap_with_node_attrs` validates the
  tag name—the render helpers are public and previously allowed markup injection through
  caller-constructed nodes (parser-assigned ids were never affected).
- `graph()` / `build_doc_graph()` accept any `collections.abc.Set`, so plain set
  literals type-check, matching `collect()` and the spec’s own examples.
- `TextUnit` is now a `StrEnum`, so its behavior matches the other public string enums.
- `DocGraph` documents `annotations`, `layout`, and `provenance` as reserved fields that
  callers must not populate until their schemas are defined.
- The footnote golden now includes a multi-block definition, pinning continuation
  paragraphs and lists as one structural footnote block.

## 3. Docs, Metadata, and Hygiene Fixed in This Pass

Applied directly (all verified by lint/tests; summary only):

- **Spec accuracy:** §3 layer table no longer claims wordtok *nodes*; §4.3 inline kinds
  include `link_ref_def`; §5 documents `HeadingInfo` alongside the other three info
  types; §15 module map now covers the full `src/flexdoc/docs/` surface; §4.1/ §4.5
  describe line-ending normalization.
- **README rewritten for first contact:** problem-led opening (parser vs NLP-toolkit
  gap), badges, a Status/maturity section, output shown for every snippet, the
  marko/flowmark foundation and never-throws posture stated, examples described
  individually, links made absolute so they work on PyPI, docs split by audience.
- **usage.md:** imports use the root surface (`from flexdoc import ...`), a
  `prose_text()` section added, `graph()` example uses plain sets, the `SpanRef` round
  trip is explained (quote = durable anchor, offsets = hint) and no longer uses a bare
  `next()`.
- **pyproject:** `keywords`, two `Topic ::` classifiers, `Homepage`/`Documentation`/
  `Changelog` URLs, template comment cruft removed.
- **Staleness:** TODO.md release steps (0.1.0/0.2.0 shipped long ago) replaced with a
  downstream-work note; extraction-plan Step 4 marked done with dates; bead
  `flexdoc-aa0l` closed.
- **Tooling:** codespell now covers the spec, AGENTS.md, TODO.md, installation.md (two
  typos it caught are fixed); `ensure-gh-cli.sh` no longer points at a nonexistent doc
  path; `examples/backfill_timestamps.py` has a module docstring.
- **Tests:** `preamble_only` golden added for headingless documents; the footnote golden
  now includes a multi-block definition; CRLF/lone-CR, shared-frontmatter-parse, and
  SpanRef ambiguity regressions added.
  Golden regeneration produces no further diffs.

## 4. Release Mechanics Before Promoting (Open; Maintainer-Gated)

- **Supply-chain refresh** (`flexdoc-r634`, P1): `exclude-newer` is 2026-05-11, about 58
  days stale against the repo’s own 14-day policy at the review date.
  The three per-package overrides (strif, flowmark, idna) are all long past their
  windows and SUPPLY-CHAIN-SECURITY.md says to remove them.
  CI currently ignores `PYSEC-2026-196` in pip and `GHSA-6v7p-g79w-8964` in msgpack;
  both are audit-tool-only dependencies with fixed versions outside the stale cutoff.
  Procedure is documented in SUPPLY-CHAIN-SECURITY.md.
  The refresh changes `uv.lock` and requires maintainer review, so it is deliberately
  not bundled into this review branch.
- **CI matrix** (P3): only `ubuntu-latest`, while the package claims `OS Independent`.
  One macOS job on one Python version is cheap confidence; or drop the classifier.
- **Local-clone version note:** wheel builds from a tagless clone produce `0.0.1.devN`
  (uv-dynamic-versioning).
  Tags `v0.1.0`/`v0.2.0` exist on the remote, so releases are fine, but
  `git fetch --tags` belongs in any release runbook that builds locally.
  (A review-pass finding claiming “no tags exist” was an artifact of the shallow CI
  clone; verified against the remote.)

## 5. Pre-1.0 API Design Decisions (Open; `flexdoc-r634`)

Breaking changes are still cheap (pre-1.0, minor-bump policy) and become reputation
costs after promotion.
Each item below was verified against the code; recommendations are mine.

1. **Context-free `SpanRef` hints cannot meet both same-source and cross-edit
   semantics.** An exact-matching offset identifies a chosen duplicate in an unchanged
   source but can silently identify the wrong duplicate after an edit.
   Without prefix/suffix or source identity, the resolver cannot distinguish those
   cases. Recommend returning `None` for duplicated, uncorroborated quotes unless a
   future source digest/revision proves the hint is current (`flexdoc-qire`).
2. **`collect(recursive=True)` excludes inline nodes** unless `inline=True`. The spec’s
   own “tally by kind” example silently omits links/code spans.
   Documented, but easy to misuse: “all descendants” is the natural reading of
   `recursive=True`. If recursion should imply inline inclusion while an explicit
   `inline=False` excludes it, the API must become tri-state (`inline: bool | None`) or
   use a separate mode; the current `False` default cannot distinguish omission from an
   override.
3. **`Section` (and `Block`) mutability versus cache sharing.** `sections()` returns a
   fresh list but shares mutable `Section` objects with the cache; mutating one corrupts
   every later read, guarded only by a docstring.
   Options: freeze the dataclasses (children as tuples, cleaner but breaking) or
   deep-copy on return (slower, compatible).
   Recommend freezing pre-1.0.
4. **`Paragraph.heading_level()`/`heading_title()` are methods; `Block.heading_level` is
   a property**, and `Paragraph.block_type`/`code_info`/`table_info` are properties two
   lines away. `if paragraph.heading_level:` is truthy for a bound method: silent wrong
   results. Recommend properties.
5. **`TRUE_LINK_FORMS` should become `NAVIGABLE_LINK_FORMS`.** Every docstring around it
   says “navigable”; the name should too.
6. **`flexdoc.docs` exports 83 symbols**, 26 of them wordtok primitives and ~10
   diff/mapping internals that exist for chopdiff.
   Recommend tiering: keep them importable from `flexdoc.docs.wordtoks`/`token_diffs`
   but drop them from `flexdoc.docs.__all__`, so the promoted surface reads as the
   document model.
7. **`resolve` is not importable where `SpanRef` is.** The root exports `SpanRef` but
   resolution lives in `flexdoc.docs`. Either export `resolve`/ `resolve_and_update`
   from the root or (cleaner, avoids the generic bare name) add
   `SpanRef.resolve(source_text)` delegating to the free function.
8. **Frontmatter delimiters reject trailing whitespace** (`--- `). Invisible editor
   spaces therefore cause detection failure.
   Decide whether to tolerate trailing spaces and tabs with `.rstrip()`; leading
   whitespace should still disqualify.
9. **`Section.size()` builds a throwaway `FlexDoc` per call** (also per unit in
   `section_size_tree`). Negligible cost (measured ~0.4µs) but structurally odd and
   motivates a circular-import workaround; extract a `size_of_paragraphs()` helper both
   can call.

Also noted, no immediate action recommended: the `DocGraph` reserved slots
(`annotations`/`layout`/`provenance`) are `list[object]`; their do-not-populate contract
is now documented. Type and version them when the first consumer lands (see §6.1).
`__version__` is absent by template convention (`importlib.metadata.version` works); add
only if downstream asks.
`.codex/` duplicates `.claude/` hook scripts by design (dual-agent support).
Add a README note only if contributors need a canonical-source explanation; JSON hook
files cannot carry comments.

## 6. AI Document Workflows: What Works Today, What to Add (`flexdoc-6582`)

The user-facing question this round: does the model actually serve LLM commenting,
review feedback, chunking, and grounded citation, and what is the smallest set of
additions that makes those workflows first-class?
Everything below was exercised against the real API, not imagined.

### 6.1 Commenting / annotation (the closest to done)

The round trip works today for refs with captured context: LLM quotes text →
`SpanRef(exact=..., prefix/suffix)` → `resolve()` → exact span.
`to_text_fragment()` encodes the quote as a URL text directive; it works directly for
visible prose, but a raw Markdown-bearing quote does not necessarily match the rendered
page text.
After edits elsewhere, the quote re-anchors, and after §2.3 an ambiguous quote
fails visibly instead of mis-anchoring.
Context-free offset hints retain the §2.3 boundary.
What is missing is the **record around the anchor**: there is no `Annotation` type, so
every consumer invents `{span_ref, kind, body, author, ...}` privately, and
`DocGraph.annotations` stays an untyped reserved list.

**Recommendation:** first decide annotation ownership and serialization.
`DocGraph` is built from a `NodeTable`, which has no annotation source, so adding an
`Annotation` model and `Detail.annotations` does not say how records enter the graph.
Decide whether annotations live on `FlexDoc`, are passed to `graph()`, or remain an
external collection.
Then define the Pydantic model, type the slot, and version the schema.
This gives the draft post a demonstrable example instead of a promise.

Complementary conveniences: `SpanRef.from_quote(exact, source_text, ...)`
(construct-and-resolve in one call, the shape an LLM’s structured output naturally
produces) and `resolve_batch(refs, source_text)` (an LLM review yields 5–50 anchors;
today each is a separate full-text scan and a hand-written loop).

### 6.2 Suggested edits / review feedback

All primitives exist (SpanRef anchors; `token_diffs` for word-level diffing; editing
view and `reassemble()`), but they do not connect: `DiffOp` positions live in the
wordtok stream with no mapping to source spans, so “show this diff anchored in the
original” has no API path.
A cleaner shape than wiring diffs to spans is a `SuggestedEdit` record with `span_ref`,
`replacement`, and attributes.
For batches, the API must also define source revision, overlapping-edit conflicts,
application order, and atomic failure behavior.
Resolve every edit against the same source, reject or explicitly order overlaps, and
apply accepted edits from highest to lowest offset.
This composes with 6.1 and leaves the diff machinery focused on windowed transforms in
Chopdiff.

### 6.3 Chunking / windowing for context budgets

Sections with per-unit sizes (including `TextUnit.tokens`), `base_blocks()` as the
partition, and `section_size_tree()` as a prompt-ready outline are a strong base.
Two gaps make the recipe non-obvious today:

- **No text accessor on `Section`:** chunkers must know to slice
  `doc.source_text[sec.span[0]:sec.span[1]]`. Add `Section.text` / `Section.own_text`
  properties (trivial, self-documenting) and `FlexDoc.preamble_text` for pre-heading
  content.
- **No machine-readable outline:** `section_size_tree()` is text-only.
  In the review sample, full `DocGraph` JSON was much larger than the rendered tree and
  carried detail a budget-sensitive prompt did not need.
  Add `section_outline()` returning `[{title, level, span, sizes, children}]`.

Also worth a usage.md recipe once these land: budget-aware windowing = walk
`section_outline()`, split oversized sections at `base_blocks()`, never at raw character
offsets.

### 6.4 Grounded citation and offset attribution

Works today: quote → span → section attribution via
`collect(overlaps=..., kinds={section})` or `table.containing(span)`. For browser
highlight links, plain-prose refs project directly; Markdown-bearing refs need a future
source-to-rendered-text projection (`flexdoc-p6xv`). One symmetry gap:
`paragraph_at_offset` and `sentence_at_offset` exist but `section_at_offset` does not;
add it (deepest section containing the offset) to complete the set and make
annotation→section display a one-liner.

### 6.5 Feeding structure to an LLM

`DocGraph`’s YAML form (`to_yaml`, empty-field suppression) is the right LLM-facing
serialization and `prose_text()` the right clean-text projection (now documented in
usage.md). No changes recommended beyond 6.3’s outline.

**Sequencing:** settle annotation ownership and schema versioning first, then add
from-quote/batch resolution and section text/outlines.
`SuggestedEdit` follows after batch conflict semantics are explicit.
Approximate re-anchoring stays opt-in and must return its strategy and score rather than
silently extending `resolve()`.

## 7. Findings That Did Not Survive Verification

For the record, claims checked and rejected: the golden corpus’s regeneration
instructions work as documented; `render.py` is tested (inline tests, extended in this
pass); usage.md snippets run as written when executed in sequence; “no git tags” was a
clone artifact (see §4); “`AtomicSpans` misnamed in spec §15”: the flowmark symbol is
legitimately referenced.
The wheel is clean (py.typed and the schema JSON ship; nothing stray), node-id
determinism and layer-nesting validation held under adversarial re-testing, and
`doc_graph_schema.json` matches the Pydantic models.

## 8. Recommended Action Plan

The staged roadmap is the task source of record:

1. Merge this review branch after its tests and CI pass; do not publish these breaking
   behavior changes as 0.2.x.
2. Complete the 0.3.0 API and release-gate stage (`flexdoc-r634`), including the
   context-free hint decision (`flexdoc-qire`) and supply-chain review.
3. Implement and validate the AI workflow primitives (`flexdoc-6582`) behind an explicit
   `DocGraph` schema version.
4. Complete downstream adoption, synthetic-layer work, and promotion (`flexdoc-ww1i`;
   existing synthetic-layer bead `flexdoc-t5rh`).

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
