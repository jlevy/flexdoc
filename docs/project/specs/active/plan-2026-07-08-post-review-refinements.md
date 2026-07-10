# Plan: Post-Review Refinements and AI-Workflow Mechanisms

**Date:** 2026-07-08

**Author:** Joshua Levy (with LLM assistance)

**Status:** Superseded on 2026-07-09 by
[`plan-2026-07-09-flexdoc-stabilization-roadmap.md`](plan-2026-07-09-flexdoc-stabilization-roadmap.md).
Retained as the initial review snapshot.

## Overview

The 2026-07 pre-promotion review
([senior-engineering-review-flexdoc-2026-07.md](../../review/senior-engineering-review-flexdoc-2026-07.md))
split its output in two: clear fixes, which landed directly on the review branch and are
recorded in `CHANGELOG.md` (Unreleased), and everything that takes a real decision or is
future work, collected here.
The 2026-07-09 roadmap corrects the tracking references, adds follow-up findings, and is
now the task source of record.
The review doc holds the evidence and argument for each item.

## Goals

- Settle the remaining pre-1.0 API-surface decisions in one batch (one breaking 0.3.0,
  not a drip of them after promotion).
- Add the minimal mechanisms that make AI annotation/commenting/chunking workflows
  first-class and demonstrable.
- Clear the release mechanics the project’s own policies call for before promotion.

## Non-Goals

- The synthetic layer (tracked separately: `flexdoc-t5rh`, extraction plan Stage 4).
- Full fuzzy/edit-distance `SpanRef` re-anchoring; only the cheap normalized-match tier
  is considered here.
- Any change already applied on the review branch (see CHANGELOG Unreleased).

## 1. Pre-1.0 API Decisions (Bead `flexdoc-r634`)

Breaking changes are cheap now (pre-1.0, minor-bump policy) and expensive after
promotion.
Recommend deciding all of these in one sitting and shipping as 0.3.0. Evidence
and detail: review doc §5.

Near-mechanical (recommend simply doing):

- [x] `Paragraph.heading_level` / `heading_title` are properties, matching
  `Block.heading_level` and `Paragraph.block_type`/`code_info`/`table_info`.
  `if paragraph.heading_level:` now reads the value rather than a truthy bound method.
  Breaking for callers using `()`; migrated in the 0.3 cleanup.
- [x] Rename `TRUE_LINK_FORMS` → `NAVIGABLE_LINK_FORMS`; the new name matches the
  surrounding API language.
  Breaking for importers and shipped without an alias in the 0.3 cleanup.
- [x] Add `SpanRef.resolve(source_text)` and `SpanRef.resolve_and_update(source_text)`
  methods delegating to the implementation functions.
  The root API stays concise and avoids generic bare resolver names; `flexdoc.docs` no
  longer promotes those names.

Need a real decision:

- [ ] **`collect(recursive=True)` and inline nodes.** Today inline kinds are excluded
  unless `inline=True` (or an inline `kinds` filter implies it); the spec’s own “tally
  by kind” example silently omits links/code spans.
  Option A: `recursive=True` implies inline inclusion, with a tri-state `inline` option
  or equivalent mode so explicit exclusion differs from omission (less surprising;
  behavioral break). Option B: keep semantics, fix the spec example, and document the
  behavior. Recommendation: A.
- [ ] **`Section`/`Block` mutability versus cache sharing.** `sections()` shares mutable
  `Section` objects with the per-doc cache; mutation corrupts later reads, guarded only
  by a docstring. Option A: freeze the dataclasses (children/content become tuples;
  breaking, correct). Option B: deep-copy on return (compatible, slower, keeps the
  mutable interface). Recommendation: A, pre-1.0.
- [x] **Tier the `flexdoc.docs` export surface.** The promoted surface now contains 44
  document-model, serialization, query, and render/report names.
  Word-token/search and diff/mapping machinery remains importable from its owning
  modules. Chopdiff `origin/main` at `df1337b` already imports these lower-level
  dependencies from owning modules; its only `flexdoc.docs` import is the promoted
  `Paragraph`, so no downstream source change is required.
- [x] **Frontmatter delimiter whitespace.** Opening and closing delimiters tolerate
  trailing spaces and tabs while leading whitespace still disqualifies them.
  Detection preserves the delimiter text and absolute body offset; an unclosed opening
  remains a thematic break.
- [ ] **`Section.size()` internals**: extract a `size_of_paragraphs(paragraphs, unit)`
  helper so `Section` stops building a throwaway `FlexDoc` per call (measured negligible
  at ~0.4µs, but removes a circular-import workaround).
  No API change.

## 2. AI Annotation/Commenting Mechanisms (Bead `flexdoc-6582`)

The smallest additions that turn the annotation/feedback story from implied to
demonstrable (review doc §6; all verified against today’s API):

- [ ] **Annotation ownership and record type**: decide whether annotations live on
  `FlexDoc`, are supplied to `graph()`, or remain external; then define
  `{span_ref, kind, body, attrs}` as a Pydantic model, type the reserved
  `DocGraph.annotations` slot, and version the schema.
- [ ] **`SpanRef.from_quote(exact, source_text, prefix=None, suffix=None)`**:
  construct-and-resolve in one call—the shape an LLM’s structured output produces.
- [ ] **`resolve_batch(refs, source_text)`**: one call for the 5–50 anchors an LLM
  review yields; opens the door to a shared occurrence index later.
- [ ] **`Section.text` / `Section.own_text` properties** (source slice at the section’s
  span) and **`FlexDoc.preamble_text`**—makes structural chunking self-documenting
  instead of requiring manual `source_text[span[0]:span[1]]`.
- [ ] **`FlexDoc.section_at_offset(offset)`**—deepest section containing an offset;
  completes the `paragraph_at_offset`/`sentence_at_offset` set and makes
  annotation→section attribution a one-liner.
- [ ] **`section_outline()`**: the `section_size_tree()` data as a JSON-serializable
  structure `[{title, level, span, sizes, children}]`—a compact skeleton for prompts and
  tools; in the review sample, full DocGraph JSON was much larger than the rendered
  tree.
- [ ] **`SuggestedEdit` type**: `{span_ref, replacement, attrs}` plus batch semantics
  for source revision, overlap conflicts, application order, and atomic failure.
  Deliberately do not wire `token_diffs` to source spans (see review doc §6.2).
- [ ] **Tiered re-anchoring (cheap middle tier)**: add an opt-in
  whitespace-collapsed/case-normalized matcher that returns its strategy and score; full
  fuzzy matching remains deferred under `flexdoc-6582`.
- [ ] A usage.md recipe for budget-aware windowing once `section_outline()` lands: walk
  the outline, split oversized sections at `base_blocks()`, never at raw character
  offsets.

Suggested sequencing: `Annotation` and `from_quote`/`resolve_batch` first, then
`Section.text` and `section_outline()`; `SuggestedEdit` follows `Annotation`.

## 3. Release Mechanics Before Promotion (Bead `flexdoc-r634`)

- [ ] **Supply-chain refresh** (maintainer-gated by policy): bump `exclude-newer` from
  2026-05-11 to (today − 14 days); remove the expired strif/flowmark/idna per-package
  overrides and their SUPPLY-CHAIN-SECURITY.md entries; `make upgrade`; re-run
  `pip-audit` and drop both audit-gate ignores from ci.yml if they clear
  (`PYSEC-2026-196` in pip; `GHSA-6v7p-g79w-8964` in msgpack, added 2026-07-08 when the
  advisory landed mid-review—both are pip-audit-only transitive deps and both fixes are
  already past their 14-day windows).
  Deliberately kept off the review branch (lockfile churn).
- [ ] **CI matrix vs. classifier**: add one macOS job (single Python version) or drop
  `Operating System :: OS Independent`.
- [ ] **Release runbook note**: local wheel builds need `git fetch --tags`
  (uv-dynamic-versioning yields `0.0.1.devN` from a tagless clone; remote tags are
  fine).

## 4. Smaller Items, No Urgency

- [ ] `__version__` attribute: absent by template convention;
  `importlib.metadata.version("flexdoc")` works.
  Add only if downstream asks.
- [ ] `.codex/` duplicates `.claude/` hook scripts by design (dual-agent support); add a
  README note or cross-reference if contributors ask which is canonical (JSON hooks
  files cannot carry comments).
- [ ] Golden corpus: a 7+-level deep list at default `item_partition_depth` would pin
  the depth cap at its default (the same branch is already pinned at depth 2); marginal
  value, add opportunistically.
- [ ] Dogfood test (`test_repo_markdown_invariants`): extend with the base-block cover
  invariant and a SpanRef round-trip check to run those guarantees over all ~105 repo
  Markdown files, not just the golden corpus.
- [ ] Insertion-point references (empty `exact` at a position) are now rejected by
  `resolve()`; if the annotation layer ever needs them, that is a deliberate schema
  extension (W3C-style position selector), not a revert.

## Testing Strategy

Each §1 item that changes behavior gets a targeted unit test in the same commit; §2
items each ship with usage-guide snippets that double as doctests of the recipe; goldens
are regenerated only when a change is intentionally behavioral, with the diff reviewed
as such (per `tests/golden/README.md`).

## References

- Review (evidence for every item):
  [senior-engineering-review-flexdoc-2026-07.md](../../review/senior-engineering-review-flexdoc-2026-07.md)
- Beads: `flexdoc-r634` (§1 and §3), `flexdoc-qire` (context-free offset hints),
  `flexdoc-6582` (§2), and `flexdoc-ww1i` (downstream adoption and promotion); related:
  `flexdoc-t5rh` (synthetic layer).
- Draft intro post:
  [draft-2026-07-flexdoc-intro-post.md](../../drafts/draft-2026-07-flexdoc-intro-post.md)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
