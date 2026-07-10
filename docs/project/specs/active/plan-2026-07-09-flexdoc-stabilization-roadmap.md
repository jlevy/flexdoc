# Feature: Staged FlexDoc Stabilization and Promotion Roadmap

**Date:** 2026-07-09 (last updated 2026-07-09)

**Author:** Joshua Levy and Codex

**Status:** Draft; maintainer decisions remain open.

## Overview

This plan consolidates the implementation history, PR #9, the 2026-07 pre-promotion
review, and the follow-up engineering review into one staged roadmap.
It supersedes `plan-2026-07-08-post-review-refinements.md`, which remains as the initial
review snapshot.

The immediate objective is a coherent 0.3.0 boundary: ship the correctness changes
already on PR #9 together with the remaining pre-1.0 API decisions, refresh the
supply-chain state, and make the public contract internally consistent.
Later releases can add annotation and synthetic-layer mechanisms without reopening that
foundation.

## Goals

- Release the current breaking behavior changes and remaining pre-1.0 API decisions as
  one documented 0.3.0 boundary
- Preserve one normalized source string and one Unicode-code-point offset space across
  every projection
- Make anchoring failures visible, including the unresolved context-free offset-hint
  case
- Add annotation, suggestion, chunking, and outline mechanisms with explicit ownership,
  conflict, and schema-version semantics
- Complete the synthetic layer and downstream Chopdiff adoption after the public API is
  stable
- Keep every stage linked to real `tbd` beads, tests, release notes, and maintained
  documentation

## Non-Goals

- Byte-exact CRLF preservation in `FlexDoc`; callers that need file-coordinate fidelity
  require a separate offset-mapping design
- Full fuzzy or edit-distance anchoring in `resolve()`; approximate recovery must remain
  opt-in and report match quality
- CRDT anchors, collaborative editing, renderer implementation, or a rich-text editor
  model
- New dependencies without the repository’s cool-off, lockfile review, audit, and human
  exception process
- Rewriting historical design records that are clearly labeled as implemented or
  superseded

## Background

PR #9 fixes CRLF span corruption, frontmatter leakage into the Markdown parse, ambiguous
exact-quote selection, empty overlap semantics, and HTML-attribute hardening.
The follow-up review also found and fixed a remaining double parse: documents with
frontmatter built links from a second body-only parse even though the blanked shared
parse was already safe to reuse.

The review also confirmed four planning gaps:

- A `SpanRef` with offsets but no prefix or suffix can still silently select the wrong
  duplicate after an edit.
  The current implementation cannot distinguish a valid same-source position from a
  stale position without context or source identity.
- The proposed `collect(recursive=True)` behavior needs a tri-state API if callers are
  to distinguish an omitted `inline` option from an explicit `inline=False` override.
- An `Annotation` model alone does not define who owns annotations or how they enter a
  `DocGraph`; the builder currently receives only a `NodeTable`.
- A `SuggestedEdit` record alone does not define batch application, overlap conflicts,
  stale anchors, or atomic failure behavior.

The supply-chain cutoff is also stale.
CI passes only because the audit job explicitly ignores two advisories in
audit-tool-only dependencies.
The repository policy requires maintainer ratification or a reviewed cutoff and lockfile
refresh before promotion.

## Tracking

- `flexdoc-r634`: Phase 1, 0.3.0 API stabilization and release gates
- `flexdoc-qire`: context-free `SpanRef` offset-hint ambiguity (child of `flexdoc-r634`)
- `flexdoc-6582`: Phase 2, source-grounded AI workflow primitives
- `flexdoc-p6xv`: rendered-text URL fragment projection (child of `flexdoc-6582`)
- `flexdoc-ww1i`: Phase 3, extensions, downstream adoption, and promotion
- `flexdoc-t5rh`: synthetic-layer implementation, linked to Phase 3
- `flexdoc-5bux`: PR #9 follow-up review and branch refinements

## Design

### Release Boundaries

- **0.3.0:** PR #9 behavior changes, anchoring contract decision, pre-1.0 API cleanup,
  and release/supply-chain gates
- **0.4.0:** additive annotation, suggestion, and structural-outline APIs plus the next
  `DocGraph` schema version
- **Later minor release:** synthetic layer and any associated cross-layer editing API

Do not publish the PR #9 changes as a 0.2.x patch.
CRLF normalization, ambiguous-quote resolution, and `TextUnit` string equality change
observable behavior and belong in the documented pre-1.0 minor release.

### Compatibility Requirements

- **Library APIs:** 0.3.0 may break APIs listed in Phase 1, with no compatibility
  aliases; every break needs a changelog migration note and root-surface contract test
- **Serialized formats:** preserve `DocGraph/v0.1`; introduce a new schema version when
  annotation fields become typed or populated
- **Source coordinates:** offsets index normalized `source_text`; external CRLF
  coordinates are unsupported unless a future mapping API is designed explicitly
- **Downstream Chopdiff:** coordinate export cleanup and the external-package rewire so
  it migrates once to the settled 0.3.0 surface

### Documentation Ownership

- `docs/flexdoc-spec.md` is the current behavioral contract
- This roadmap owns future sequencing and decisions
- Review documents record evidence and conclusions; they do not remain parallel task
  lists
- Implemented plans should move to the archive after their remaining deferred work is
  linked here or to a dedicated successor plan

## Implementation Plan

### Phase 1: Stabilize the 0.3.0 Contract and Release Gates

- [ ] Ratify normalize-at-parse for CRLF/lone-CR input and frontmatter blanking as the
  supported coordinate model; keep the current regression corpus
- [ ] Resolve context-free offset hints in `SpanRef`:
  - Option A, recommended: when `exact` is duplicated and no context or source identity
    corroborates the hint, return `None`
  - Option B: add source identity/revision data and trust the hint only when it matches
  - Do not keep the current blanket “stale hints are harmless” claim without one of
    these constraints
- [ ] Settle the pre-1.0 API batch:
  - Convert `Paragraph.heading_level()` and `heading_title()` to properties
  - Rename `TRUE_LINK_FORMS` to `NAVIGABLE_LINK_FORMS`
  - Put resolution beside `SpanRef` through methods or deliberate root exports
  - Decide recursive inline semantics; use `inline: bool | None` or an equivalent mode
    if explicit exclusion must differ from the default
  - Freeze `Section` and `Block` graphs or return defensive deep copies
  - Tier `flexdoc.docs` exports in coordination with the Chopdiff rewire
  - Decide trailing-whitespace tolerance for frontmatter delimiters
  - Extract paragraph-size aggregation so `Section.size()` avoids a temporary `FlexDoc`
- [ ] Refresh the supply-chain cutoff and lockfile under maintainer review, remove
  expired package overrides, and remove audit ignores that the refreshed environment no
  longer needs; otherwise record explicit maintainer ratification for each temporary
  ignore
- [ ] Add one macOS CI job or remove the OS-independent classifier
- [ ] Update the release runbook to fetch tags before local dynamic-version builds
- [x] Close stale root-API beads whose implementation and contract tests already landed
  (`flexdoc-l0lc`, `flexdoc-bift`; closed 2026-07-09)
- [ ] Run lint, the full suite, golden regeneration, wheel smoke, and the unignored
  audit; publish 0.3.0 only when the chosen security gate passes

### Phase 2: Add Source-Grounded AI Workflow Primitives

- [ ] Define annotation ownership before the model:
  - Decide whether annotations live on `FlexDoc`, are passed to `graph()`, or remain an
    external collection serialized alongside `DocGraph`
  - Define ids, kinds, body format, JSON-safe attributes, provenance, and validation
  - Version the schema and specify v0.1/v0.2 reader behavior
- [ ] Add `SpanRef.from_quote()` and `resolve_batch()` with the same ambiguity contract
  as single resolution; measure before adding a shared occurrence index
- [ ] Define rendered-text fragment export: either accept an explicit rendered-text ref
  or add a source-to-rendered-text projection, with tests for Markdown links, emphasis,
  code, and plain prose
- [ ] Add `Section.text`, `Section.own_text`, `FlexDoc.preamble_text`,
  `section_at_offset()`, and a JSON-serializable `section_outline()`
- [ ] Define `SuggestedEdit` and batch application semantics:
  - Resolve every anchor against the same source revision
  - Reject or explicitly order overlapping edits
  - Apply accepted edits from highest to lowest offset
  - Return per-edit outcomes and avoid partial mutation on batch failure
- [ ] Keep approximate re-anchoring separate from `resolve()` and return the strategy
  and score; begin with normalization-only matching and add fuzzy matching only with
  corpus evidence
- [ ] Add runnable annotation, suggestion, grounded-citation, and budget-aware chunking
  examples to `docs/usage.md`
- [ ] Extend unit, invariant, and golden coverage for ambiguity, batch conflicts, schema
  compatibility, and round trips

### Phase 3: Complete Extensions, Downstream Adoption, and Promotion

- [ ] Implement the synthetic marker-tag layer with a documented partial-overlap policy
  and node-table nesting invariants
- [ ] Rewire Chopdiff to the external FlexDoc release and the tiered export surface in
  one migration
- [ ] Exercise the annotation and chunking APIs in at least one downstream workflow
  before presenting them as established capabilities
- [ ] Update and publish the introduction post with runnable examples that use released
  APIs
- [ ] Archive implemented and superseded plans; keep the spec, this roadmap, TODO, and
  beads mutually consistent

## Testing Strategy

- Follow red-green-refactor for each behavior change; keep the smallest regression that
  reproduces each failure
- Preserve the golden corpus as the broad behavioral view and keep independent
  invariants for spans, cover, tree relationships, and serialization
- Add contract tests for every root export, breaking migration, and `DocGraph` schema
  version
- Test anchoring against duplicate quotes, missing context, stale hints, edited context,
  and overlapping suggestion batches
- Run all supported Python versions in CI and one macOS job if the OS-independent claim
  remains
- Run `make lint`, `make test`, golden regeneration, wheel smoke, and `pip-audit` before
  every release

## Rollout Plan

1. Merge PR #9 after its branch tests and CI pass; do not publish it as 0.2.x.
2. Complete Phase 1 and publish 0.3.0 with a migration-focused changelog.
3. Complete Phase 2 behind the next `DocGraph` schema version and publish 0.4.0.
4. Complete Phase 3 only after downstream adoption validates the extension APIs.

## Open Questions

- Will the maintainer ratify the current audit ignores temporarily, or require the
  cutoff and lockfile refresh before PR #9 merges?
- Should a context-free positional hint select a duplicate in an unchanged source, and
  if so, what source identity proves that the source is unchanged?
- Should recursive collection include inline nodes by default, and what explicit API
  excludes them?
- Should cached structural objects be immutable, or should public methods return deep
  copies?
- Who owns annotations, and how are they supplied to `DocGraph` serialization?
- Does a populated annotation layer require `DocGraph/v0.2` on every graph or only on
  graphs that include annotations?
- Is macOS CI required, or should package metadata narrow the platform claim?

## References

- PR [#9](https://github.com/jlevy/flexdoc/pull/9)
- [2026-07 senior engineering review](../../review/senior-engineering-review-flexdoc-2026-07.md)
- [FlexDoc design specification](../../../flexdoc-spec.md)
- [Initial post-review refinements plan](plan-2026-07-08-post-review-refinements.md)
- [Extraction plan](plan-2026-06-11-flexdoc-extraction.md)
- [W3C Web Annotation selectors](https://www.w3.org/TR/annotation-model/#selectors)
- [URL Fragment Text Directives](https://wicg.github.io/scroll-to-text-fragment/)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
