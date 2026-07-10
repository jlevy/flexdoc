# Senior Engineering Review: FlexDoc Standalone (Post-Extraction)

**Date:** 2026-06-12

**Scope:** the extracted standalone flexdoc package at Stage 2 of
[`plan-2026-06-11-flexdoc-extraction.md`](../specs/active/plan-2026-06-11-flexdoc-extraction.md):
all of `src/flexdoc/` (`docs/`, `html/`, `util/`), the design of record
([`docs/flexdoc-spec.md`](../../flexdoc-spec.md)), the test suite, and packaging.
Builds on the v0.3.1 review (in chopdiff,
`docs/project/review/senior-engineering-review-doc-model-v0.3.1.md`); findings settled
there are re-verified here, not re-argued.

**Review mode:** static review of the code at this commit plus verification runs
(`make lint` clean; `make test` 305 passed; wheel built and smoke-imported in an
isolated venv). Claims below were checked against the source; two inventory claims that
did not survive verification are noted in §6.

**Context for this review:** flexdoc is about to publish its first release (0.1.0).
chopdiff will be rewired to the published package afterward and can absorb breaking
changes at that point.
This is therefore the **one cheap window for breaking API cleanups**: anything that
breaks after 0.1.0 costs a migration; the same change today costs nothing.
The bar for “fix now” is correspondingly lower than usual, and the bar for shipping
known cruft in 0.1.0 is higher.

* * *

## 1. Executive Verdict

The architecture is settled and right, and the extraction did not bend it: one immutable
source string and one Unicode-code-point offset space as the canonical substrate, with
the node table, block tree, sections, links, and base-block partition as sibling
projections over one shared parse.
The v0.3.1 review’s eight P1 findings are all addressed in the current code (§2), the
package stands alone with no chopdiff dependency, and the suite (unit + golden +
supply-chain guard) is green.

What remains is not architecture but **first-release hygiene**: migration cruft that
should not appear in a brand-new package’s API (deprecated aliases), an export surface
with real gaps (typed block metadata and the `SpanRef` resolvers are not importable from
`flexdoc.docs`), one terminology seam the spec itself warns about but the API still
violates (editing-view methods named “block”), and a 1300-line module the previous
review already asked to split.
All of these are cheap now and expensive later.

**Recommended stance:** insert a short pre-publish refinement stage (Stage 2.5 in the
extraction plan) and land it before tagging 0.1.0, so the first published API is the one
we want to keep. Defer the deep redesigns (wordtok sentinel typing, analyzer interface,
annotation layer) to Stage 3 as planned—none of them block a clean 0.1.0.

## 2. Status of the v0.3.1 Review Findings (Verified in This Tree)

| v0.3.1 finding | Status now | Evidence |
| --- | --- | --- |
| Docs showed a `DocGraph` query API that did not exist | Fixed | Spec §9/§10 describe `doc.collect(...)` and `doc.graph(...)`; `DocGraph` is serialization-only (`doc_graph.py`) |
| `collect(scope=...)` was subtree-only | Fixed (aliases linger) | `collect.py:32` has `subtree_of`/`within`/`overlaps`; `scope`/`contains` remain as deprecated aliases—see F1 |
| Inline kinds required `inline=True` | Fixed | `collect.py:96`: explicit inline `kinds` implies inline inclusion |
| Sections built from the paragraph view | Fixed | `text_doc.py:764`: headings gated on top-level structural heading blocks via bisect over `blocks()` |
| `set_sent()` dropped `original_text` | Fixed | `text_doc.py:905` preserves it, with the contract in a comment |
| `SpanRef` fragment unencoded; `resolve()` mutated | Fixed | `span_ref.py:29` percent-encodes (incl. `-`/`,`); `resolve()` pure, `resolve_and_update()` explicit |
| Cached projections poisonable | Addressed differently | No `DocumentSnapshot`; instead lock-guarded idempotent caches with a documented read-contract (`text_doc.py:509-602`), defensive list copies in `blocks()`/`links()`, frozen `Link`. Acceptable; revisit only on evidence of misuse |
| Node-table assembly super-linear | Fixed | `node_table.py:145` builds an `IntervalIndex` for inline/section attribution |
| P3 items (tests in `node.py`, `pop(0)`, `included_ids`, `block_type_counts`) | All fixed | Verified by grep; `collect.py:15` uses `deque` |

The one structural suggestion not taken—the frozen `DocumentSnapshot`—was replaced by a
documented, tested caching contract (`tests/docs/test_caching_threadsafe.py`). That is a
legitimate lighter-weight answer.
Do not build the snapshot type speculatively; reconsider only if real misuse shows up.

## 3. Findings to Fix Before 0.1.0 (P1)

### F1. Deprecated aliases must not ship in a first release

`collect()` still accepts `scope` (positional!)
and `contains` as deprecated aliases for `subtree_of`/`within`
(`collect.py:34,39,59-75`; mirrored in `TextDoc.collect`, `text_doc.py:1161-1191`).
These exist solely to migrate chopdiff-internal callers—a constituency that no longer
exists for this package.
A new package whose first release documents “deprecated alias, do not use” invites every
future client to carry that cruft forever.

Drop both aliases and the positional `scope` slot; make `collect()` fully keyword-only
after `table`. Rewrite the alias-behavior tests
(`tests/docs/test_collect.py:127,170,198,255,328,335,361`) to the modern names (the
alias-error test cases simply disappear).
chopdiff’s rewire (extraction plan Step 5) must use the modern names—its `transforms`
already do.

### F2. The export surface has real gaps; settle it once

Verified missing from `flexdoc.docs.__init__` while being public API in substance:

- `CodeInfo`, `TableInfo`, `ListInfo` (`block_info.py`)—exposed as `Block.code_info`
  etc. and flattened into node `attrs` (spec §5), but the *types* cannot be imported from
  `flexdoc.docs` for annotations or `isinstance` checks.
- `resolve`, `resolve_and_update` (`span_ref.py:103,146`)—`SpanRef` is exported but the
  functions that resolve one are not.
- `parse_blocks`, `walk_blocks` (`block_tree.py`), `block_type_for` (`block_types.py`) —
  used by examples/tests via deep module paths.
- `flexdoc.html`: `html_p`, `html_tag`, `escape_attribute`, `tag_wrapper`,
  `identity_wrapper` are public in `html_in_md.py` but absent from `__all__` while their
  siblings (`html_a`, `div_wrapper`, ...) are exported—an arbitrary split in one
  coherent family.

Also: `text_doc.py:32` imports `_DEFAULT_INCLUDE` from `doc_graph`—a private-by-name
constant feeding a public default.
Rename it `DEFAULT_INCLUDE` and export it (callers of `graph()` legitimately want to
extend the default set).

Recommendation: one deliberate pass deciding, per symbol, exported or underscore-private
— export the items above; keep `IntervalIndex` and the `node_table`/`render` internals
private (rename with `_` where cheap, or leave module-private by convention).
This is exactly the “settle the surface” work that is much harder after 0.1.0.

### F3. The editing-view “block” naming contradicts the model’s own terminology

Spec §6 works hard to fix vocabulary ("block element" / “block node” / “base block”)
precisely because “block” is overloaded.
The API then breaks the discipline in the editing view: `TextDoc.block_at_offset()`
(`text_doc.py:736`) returns a *`Paragraph`* (a blank-line unit), and
`iter_blocks()`/`filtered()` (`text_doc.py:1016,1039`) iterate/filter *paragraphs* by
`BlockType`—while `blocks()` and `base_blocks()` return structural nodes.
A new user reading `block_at_offset` next to `blocks()` will assume they speak the same
language; they do not (a fenced code block with internal blank lines is one `Block` but
several `Paragraph`s).

Recommendation (breaking, sanctioned now): rename `block_at_offset` →
`paragraph_at_offset`; `iter_blocks` → `iter_paragraphs`; keep `filtered()` (its name
does not claim “block”) but rephrase its docstring in paragraph terms.
Mirror the rename in `Section.own_blocks()`/`subtree_blocks()` → `own_paragraphs()`/
`subtree_paragraphs()` (`text_doc.py:1256,1273`); `Section.blocks()` keeps its name—it
genuinely returns structural `Block`s. After this, “block” always means the structural
layer, “paragraph” always means the editing view, and the spec’s terminology matches the
API everywhere.

## 4. Medium-Priority Findings (P2; Pre-Publish Preferred, Not Blocking)

### F4. Split `text_doc.py`

1312 lines holding eight concerns (`TextDoc`, `Paragraph`/`Sentence`/`Offsets`/
`SentIndex`, `Link` + recovery heuristics, `Section`, sizing, the wordtok bridge, the
`collect`/`graph` bridges, caching infrastructure).
The v0.3.1 review’s split (editing / links / sections, with `flexdoc.docs` re-exports
keeping every public import stable) is still right and is purely internal—no API break
if done at the package surface.
Doing it before 0.1.0 means external links to source lines never break.

### F5. Memoize `sections()` (and thereby `toc()`)

`sections()` rebuilds the tree on every call (`text_doc.py:764`); `toc()` and
`section_size_tree()` each call it again.
It is a pure function of the immutable source and the memoization infrastructure
(`_memoized_derivation`) already exists for parse/blocks/links/node-table.
One decorator plus a `_cached_sections` field.
(The same lazy-list copy discipline as `blocks()` applies, since `Section` is mutable.)

### F6. Tighten `Node.attrs` for the cross-language contract

`attrs: dict[str, object]` (`node.py:96`) is looser than a frozen `DocGraph/v0.1` schema
should be. Define a JSON-safe value alias
(`AttrValue = str | int | float | bool | None | list[...] | dict[str, ...]`) and
validate at `DocGraph` emission (Pydantic can enforce it on `NodeModel.attrs`), so a
Rust/TypeScript client can rely on the schema.
Also pin node-id assignment order in a schema test (the v0.3.1 review’s “ports produce
different ids” risk)—the golden docgraph fixtures already freeze this de facto; make the
guarantee explicit in the spec.

### F7. Enforce `LAYER_NESTING` at table build

`LAYER_NESTING` (`node.py:74`) declares tree vs ordered-list guarantees per layer but
nothing checks them.
A cheap validation in `build_node_table` (tree layers: single parent, no span crossing
among siblings) turns a future synthetic-layer bug into an immediate error instead of a
silent contract violation.
Matters before the synthetic layer lands (extraction plan Stage 4).

## 5. Lower-Priority Findings (P3) and Explicit Non-Actions

- **Linear offset lookups.** `block_at_offset`/`sentence_at_offset` scan
  (`text_doc.py:736,748`); `collect()`'s interval relations scan all nodes
  (`collect.py:87-92`). Fine at documented scale; `IntervalIndex` exists if a benchmark
  ever says otherwise.
  Do nothing without a benchmark.
- **Naming consistency pass (cosmetic).** `wordtokenize` vs `wordtok_to_str`;
  exported-vs-not in the `html_*` family (covered by F2). Fold into F2’s pass; do not
  churn names that downstream transforms use heavily (`wordtoks` constants stay).
- **Coverage gaps.** `visualize_wordtoks`, `escape_attribute`, `html_p`/`html_tag`, the
  `render.py` helpers, and `find_best_alignment` lack direct tests (several have inline
  tests only). Add targeted tests opportunistically when F2 settles what is public; none
  blocks release.
- **Docs still chopdiff-framed in places.** Spec §3/§6 say “chopdiff parses…”
  (`flexdoc-spec.md:193,334`); §13’s non-goal lists “FlexDoc” as a *rejected runtime
  model name*, colliding with the package name—needs the disambiguation note (already a
  Stage 5 item). The copied plan specs and research briefs should get one-line origin
  notes.
- **`flexdoc.util.read_time` has zero internal users** (verified).
  It is a downstream convenience (kash/pprose).
  Keep it—it is 56 lines and cohesive with `token_estimate`—but say so in its docstring
  rather than letting it look like dead code.
- **Do not** redesign the wordtok sentinel strings (`<-SENT-BR->` et al.,
  `wordtoks.py:17-20`). Stringly-typed but deeply load-bearing for chopdiff’s
  diff/window machinery; typed tokens are a Stage 3+ question with its own spec.
- **Do not** add root-level re-exports yet (deliberate, recorded in
  `flexdoc/__init__.py`; Stage 3 settles the top surface).
- **Do not** unify Pydantic/dataclass usage.
  The split is motivated, not accidental: Pydantic exactly at the serialization boundary
  (`doc_graph.py`, where schema emission and validation pay their way), plain
  dataclasses for the hot in-memory model (`Node`, `Block`, `SpanRef`). Document the
  rationale in `doc_graph.py`’s module docstring; changing it would buy consistency at
  runtime cost and no capability.
- **Frontmatter parser swap (tracked, blocked upstream).** `frontmatter.py` is a
  deliberate hand-rolled stopgap: the `frontmatter-format` library is file-only today;
  its string API (`fmf_split_frontmatter_string`, upstream PR pending) will replace
  `split_frontmatter` once released—with `strict=False` semantics preserved (a leading
  `---` with no close stays a thematic break, `frontmatter.py:25-26`) and a supply-chain
  cool-off exception for the fresh release (maintainer sign-off required).
  Until then the module is correct and tested; do not swap early.

## 6. Corrections to the Breadth Inventory (Claims That Did Not Verify)

Two findings from the API-surface inventory pass were checked and are **not** issues:

- *“`doc_graph_schema.json` is not included in the wheel.”* False—verified by listing
  the built wheel: hatchling packages it (`flexdoc/docs/doc_graph_schema.json` present).
  The file is referenced only by a test via the source tree, so nothing at runtime
  depends on it either way.
- *“`cached_property` first-access races on `Paragraph`.”* Not a bug: benign concurrent
  recompute of a pure function with atomic attribute assignment, explicitly covered by
  the documented read contract (`text_doc.py:592-597`). No action.

## 7. Recommended Action Plan

Land as **Stage 2.5—pre-publish design refinement** in the extraction plan, before
tagging 0.1.0 (checklist there is normative; summary):

1. F1: drop `scope`/`contains` aliases; keyword-only `collect()`; rewrite alias tests.
2. F3: editing-view renames (`paragraph_at_offset`, `iter_paragraphs`,
   `Section.own_paragraphs`/`subtree_paragraphs`).
3. F2: one export-surface pass over `flexdoc.docs` and `flexdoc.html` (+
   `DEFAULT_INCLUDE` rename); update README/examples to the settled imports.
4. F4: split `text_doc.py` with stable package re-exports.
5. F5: memoize `sections()`.
6. F6/F7: `attrs` JSON-value typing + node-id-order schema test; `LAYER_NESTING`
   validation in `build_node_table`.
7. P3 sweep: spec reframe (chopdiff→flexdoc, §13 disambiguation note), origin notes on
   copied docs, targeted tests for newly-settled exports.

Each step keeps `make lint`/`make test` green and goldens unchanged (renames touch
Python surfaces, not parse behavior).
After Stage 2.5: publish 0.1.0 (plan Step 4), then rewire chopdiff (Step 5) against the
refined names in one pass.

## 8. Bottom Line

The model is the right shape and the hard work (the boundary, the layered substrate, the
query/partition split) is done and verified.
Spend one short stage scrubbing the first-release surface—aliases out, exports settled,
the one naming seam closed, the big module split—and 0.1.0 ships an API with no
apologies in it. Everything deeper is already correctly parked in Stages 3–5.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
