# Plan: Post-Review Refinements and AI-Workflow Mechanisms

**Date:** 2026-07-08

**Author:** Joshua Levy (with LLM assistance)

**Status:** Draft — decisions open; nothing here is committed work.

## Overview

The 2026-07 pre-promotion review
([senior-engineering-review-flexdoc-2026-07.md](../../review/senior-engineering-review-flexdoc-2026-07.md))
split its output in two: clear fixes, which landed directly on the review branch and
are recorded in `CHANGELOG.md` (Unreleased), and everything that takes a real
decision or is future work — collected here.
Each section notes its tracking bead.
This plan is the single place to decide these; the review doc holds the evidence and
argument for each.

## Goals

- Settle the remaining pre-1.0 API-surface decisions in one batch (one breaking
  0.3.0, not a drip of them after promotion).
- Add the minimal mechanisms that make AI annotation/commenting/chunking workflows
  first-class and demonstrable.
- Clear the release mechanics the project's own policies call for before promotion.

## Non-Goals

- The synthetic layer (tracked separately: `flexdoc-t5rh`, extraction plan Stage 4).
- Full fuzzy/edit-distance `SpanRef` re-anchoring (`flexdoc-z09f`); only the cheap
  normalized-match tier is considered here.
- Any change already applied on the review branch (see CHANGELOG Unreleased).

## 1. Pre-1.0 API decisions (bead `flexdoc-lcuh`)

Breaking changes are cheap now (pre-1.0, minor-bump policy) and expensive after
promotion. Recommend deciding all of these in one sitting and shipping as 0.3.0.
Evidence and detail: review doc §5.

Near-mechanical (recommend simply doing):

- [ ] `Paragraph.heading_level()` / `heading_title()` become properties, matching
  `Block.heading_level` and `Paragraph.block_type`/`code_info`/`table_info`.
  Today `if paragraph.heading_level:` is truthy for the bound method — silent wrong
  results. Breaking for callers using `()`.
- [ ] Rename `TRUE_LINK_FORMS` → `NAVIGABLE_LINK_FORMS` (every surrounding docstring
  already says "navigable"; alternative name: `DEFAULT_LINK_FORMS`). Breaking for
  importers.
- [ ] Export `resolve`/`resolve_and_update` from the package root, or add a
  `SpanRef.resolve(source_text)` method delegating to the free function (avoids the
  generic bare name at root; recommended). Today `SpanRef` is a root export but its
  resolvers are not.

Need a real decision:

- [ ] **`collect(recursive=True)` and inline nodes.** Today inline kinds are excluded
  unless `inline=True` (or an inline `kinds` filter implies it); the spec's own
  "tally by kind" example silently omits links/code spans. Option A: `recursive=True`
  implies inline inclusion, `inline=False` as explicit override (less surprising;
  behavioral break). Option B: keep semantics, fix the spec example and document the
  footgun. Recommendation: A.
- [ ] **`Section`/`Block` mutability vs. cache sharing.** `sections()` shares mutable
  `Section` objects with the per-doc cache; mutation corrupts later reads, guarded
  only by a docstring. Option A: freeze the dataclasses (children/content become
  tuples; breaking, correct). Option B: deep-copy on return (compatible, slower,
  keeps the mutable interface). Recommendation: A, pre-1.0.
- [ ] **Tier the `flexdoc.docs` export surface.** 83 symbols, of which ~26 wordtok
  primitives and ~10 diff/mapping internals exist for chopdiff. Option: drop them
  from `flexdoc.docs.__all__` (still importable from
  `flexdoc.docs.wordtoks`/`token_diffs`), keeping the promoted surface the document
  model. Decide together with chopdiff's rewire (extraction plan Step 5) so the
  moved imports land once.
- [ ] **Frontmatter delimiter whitespace.** `--- ` (trailing spaces/tabs) is rejected
  today (documented, but Jekyll/Hugo/gray-matter tolerate it; invisible editor
  spaces cause silent detection failure). Proposed: `.rstrip()` both delimiter
  checks — trailing tolerance only; leading whitespace still disqualifies.
- [ ] **`Section.size()` internals**: extract a `size_of_paragraphs(paragraphs, unit)`
  helper so `Section` stops building a throwaway `FlexDoc` per call (measured
  negligible at ~0.4µs, but removes a circular-import workaround). No API change.

## 2. AI annotation/commenting mechanisms (bead `flexdoc-86iy`)

The smallest additions that turn the annotation/feedback story from implied to
demonstrable (review doc §6; all verified against today's API):

- [ ] **`Annotation` record type**: `{span_ref, kind, body, attrs}` as a Pydantic
  model in `doc_graph.py`; type the reserved `DocGraph.annotations` slot
  `list[Annotation]`; add `Detail.annotations`. Additive schema change
  (v0.1 → v0.2).
- [ ] **`SpanRef.from_quote(exact, source_text, prefix=None, suffix=None)`**:
  construct-and-resolve in one call — the shape an LLM's structured output produces.
- [ ] **`resolve_batch(refs, source_text)`**: one call for the 5–50 anchors an LLM
  review yields; opens the door to a shared occurrence index later.
- [ ] **`Section.text` / `Section.own_text` properties** (source slice at the
  section's span) and **`FlexDoc.preamble_text`** — makes structural chunking
  self-documenting instead of requiring manual `source_text[span[0]:span[1]]`.
- [ ] **`FlexDoc.section_at_offset(offset)`** — deepest section containing an
  offset; completes the `paragraph_at_offset`/`sentence_at_offset` set and makes
  annotation→section attribution a one-liner.
- [ ] **`section_outline()`**: the `section_size_tree()` data as a JSON-serializable
  structure `[{title, level, span, sizes, children}]` — a compact skeleton for
  prompts and tools (DocGraph is ~50x heavier for the same outline).
- [ ] **`SuggestedEdit` type**: `{span_ref, replacement, attrs}`; accept = resolve +
  splice + re-parse. Composes with `Annotation` (kind = `suggestion`); deliberately
  does NOT wire `token_diffs` to source spans (see review doc §6.2).
- [ ] **Tiered re-anchoring (cheap middle tier)**: on exact-match failure, try
  whitespace-collapsed/case-normalized matching before returning `None`; full fuzzy
  matching stays in `flexdoc-z09f`.
- [ ] A usage.md recipe for budget-aware windowing once `section_outline()` lands:
  walk the outline, split oversized sections at `base_blocks()`, never at raw
  character offsets.

Suggested sequencing: `Annotation` + `from_quote`/`resolve_batch` first, then
`Section.text` + `section_outline()`; `SuggestedEdit` falls out of `Annotation`.

## 3. Release mechanics before promotion (bead `flexdoc-pcac`)

- [ ] **Supply-chain refresh** (maintainer-gated by policy): bump `exclude-newer`
  from 2026-05-11 to (today − 14 days); remove the expired strif/flowmark/idna
  per-package overrides and their SUPPLY-CHAIN-SECURITY.md entries; `make upgrade`;
  re-run `pip-audit` and drop both audit-gate ignores from ci.yml if they clear
  (`PYSEC-2026-196` in pip; `GHSA-6v7p-g79w-8964` in msgpack, added 2026-07-08 when
  the advisory landed mid-review — both are pip-audit-only transitive deps and both
  fixes are already past their 14-day windows). Deliberately kept off the review
  branch (lockfile churn).
- [ ] **CI matrix vs. classifier**: add one macOS job (single Python version) or
  drop `Operating System :: OS Independent`.
- [ ] **Release runbook note**: local wheel builds need `git fetch --tags`
  (uv-dynamic-versioning yields `0.0.1.devN` from a tagless clone; remote tags are
  fine).

## 4. Smaller items, no urgency

- [ ] `__version__` attribute: absent by template convention;
  `importlib.metadata.version("flexdoc")` works. Add only if downstream asks.
- [ ] `.codex/` duplicates `.claude/` hook scripts by design (dual-agent support);
  add a README note or cross-reference if contributors ask which is canonical
  (JSON hooks files cannot carry comments).
- [ ] Golden corpus: a 7+-level deep list at default `item_partition_depth` would
  pin the depth cap at its default (the same branch is already pinned at depth 2);
  marginal value, add opportunistically.
- [ ] Dogfood test (`test_repo_markdown_invariants`): extend with the base-block
  cover invariant and a SpanRef round-trip check to run those guarantees over all
  ~105 repo Markdown files, not just the golden corpus.
- [ ] Insertion-point references (empty `exact` at a position) are now rejected by
  `resolve()`; if the annotation layer ever needs them, that is a deliberate schema
  extension (W3C-style position selector), not a revert.

## Testing Strategy

Each §1 item that changes behavior gets a targeted unit test in the same commit;
§2 items each ship with usage-guide snippets that double as doctests of the recipe;
goldens are regenerated only when a change is intentionally behavioral, with the
diff reviewed as such (per `tests/golden/README.md`).

## References

- Review (evidence for every item):
  [senior-engineering-review-flexdoc-2026-07.md](../../review/senior-engineering-review-flexdoc-2026-07.md)
- Beads: `flexdoc-lcuh` (§1), `flexdoc-86iy` (§2), `flexdoc-pcac` (§3);
  related: `flexdoc-t5rh` (synthetic layer), `flexdoc-z09f` (fuzzy re-anchoring).
- Draft intro post:
  [draft-2026-07-flexdoc-intro-post.md](../../drafts/draft-2026-07-flexdoc-intro-post.md)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
