# Feature: Staged FlexDoc Stabilization and Promotion Roadmap

**Date:** 2026-07-09 (last updated 2026-07-14)

**Author:** Joshua Levy and Codex

**Status:** In progress; Phase 1 is complete and 0.3.0 was published 2026-07-11.
Later-stage design decisions remain open.

## Overview

This plan consolidates the implementation history, PR #9, the 2026-07 pre-promotion
review, and the follow-up engineering review into one staged roadmap.
It supersedes `plan-2026-07-08-post-review-refinements.md`, which remains as the initial
review snapshot.

The immediate objective is a coherent 0.3.0 boundary: ship the correctness changes
already on PR #9 together with the remaining pre-1.0 API decisions, refresh the
supply-chain state, and make the public contract internally consistent.
The 0.4.0 phase adds native TextRef references, contextual annotations, and related
workflow mechanisms without reopening that foundation.

## Goals

- Release the current breaking behavior changes and remaining pre-1.0 API decisions as
  one documented 0.3.0 boundary
- Preserve one normalized source string and one Unicode-code-point offset space across
  every projection
- Make anchoring failures visible, including context-free offset hints over duplicate
  quotes
- Add native TextRef mapping, contextual annotations, suggestions, chunking, and
  outlines with explicit ownership, conflict, and schema-version semantics
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

The review also confirmed two planning gaps:

- An `Annotation` model alone does not define who owns annotations or how they enter a
  `DocGraph`; the builder currently receives only a `NodeTable`.
- A `SuggestedEdit` record alone does not define batch application, overlap conflicts,
  stale anchors, or atomic failure behavior.

The supply-chain cutoff and lockfile were refreshed on 2026-07-09. All expired package
exceptions and audit ignores are removed, and the unignored audit passes.

## Tracking

- `flexdoc-aqjg`: top-level execution epic for this specification
- `flexdoc-r634`: Phase 1, stabilize and release FlexDoc 0.3.0
- `flexdoc-6582`: Phase 2, add source-grounded workflow APIs and release 0.4.0
- `flexdoc-4imy`: implementation epic for the native TextRef integration specified in
  `plan-2026-07-14-native-textref-integration.md`
- `flexdoc-ww1i`: Phase 3, complete extensions, downstream adoption, and promotion
- `flexdoc-z09f`: optional fuzzy anchoring after the normalized matching corpus; not a
  0.4.0 release gate
- `flexdoc-le2a`: preparation of the execution graph in this document

The PR #9 follow-up review (`flexdoc-5bux`) is complete.
The broad AI-workflow placeholder (`flexdoc-86iy`) is superseded by the bounded Phase 2
beads below.

## Design

### Release Boundaries

- **0.3.0:** PR #9 behavior changes, anchoring contract decision, pre-1.0 API cleanup,
  and release/supply-chain gates
- **0.4.0:** additive TextRef, contextual annotation, suggestion, and structural-outline
  APIs plus `DocGraph/v0.2`
- **Later minor release:** synthetic layer and any associated cross-layer editing API

Do not publish the PR #9 changes as a 0.2.x patch.
CRLF normalization, ambiguous-quote resolution, and `TextUnit` string equality change
observable behavior and belong in the documented pre-1.0 minor release.

### Compatibility Requirements

- **Library APIs:** 0.3.0 may break APIs listed in Phase 1, with no compatibility
  aliases; every break needs a changelog migration note and root-surface contract test
- **0.4 library APIs:** additive; preserve the released `SpanRef` surface while new
  persisted workflows use typed TextRef results
- **Serialized formats:** preserve `DocGraph/v0.1`; introduce a new schema version when
  annotation fields become typed or populated
- **Source coordinates:** offsets index normalized `source_text`; external CRLF
  coordinates are unsupported unless a future mapping API is designed explicitly
- **Downstream Chopdiff:** coordinate export cleanup and the external-package rewire so
  it migrates once to the settled 0.3.0 surface

### Documentation Ownership

- `docs/flexdoc-spec.md` is the current behavioral contract
- This roadmap owns future sequencing and decisions
- `plan-2026-07-14-native-textref-integration.md` owns the focused TextRef API and
  implementation design
- Review documents record evidence and conclusions; they do not remain parallel task
  lists
- Implemented plans should move to the archive after their remaining deferred work is
  linked here or to a dedicated successor plan

## Implementation Plan

The graph separates work that can proceed in parallel from gates that require a released
contract. Every implementation bead includes focused tests, documentation, and an
explicit completion condition; testing is part of each change rather than a later
cleanup pass.

```mermaid
flowchart TD
    PR9["flexdoc-lv8m: Merge PR #9"] --> Anchor["flexdoc-qire: Settle anchor hints"]
    PR9 --> API["flexdoc-lcuh: API cleanup children"]
    Anchor --> Resolver["flexdoc-p60e: Public resolution path"]
    Resolver --> R03["flexdoc-63p5: Release 0.3.0"]
    API --> R03
    Supply["flexdoc-pcac: Supply-chain gate"] --> R03
    Platform["flexdoc-ek6u: Platform contract"] --> R03
    Runbook["flexdoc-44b1: Release workflow"] --> R03
    R03 --> AI["Phase 2 API beads"]
    AI --> Examples["flexdoc-vav2: Workflow validation"]
    Examples --> R04["flexdoc-f4mz: Release 0.4.0"]
    R03 --> Synthetic["flexdoc-t5rh: Synthetic layer"]
    Synthetic --> Chopdiff["flexdoc-19h2: Chopdiff migration"]
    Chopdiff --> Pilot["flexdoc-b8a4: Downstream pilot"]
    R04 --> Pilot
    Pilot --> Publish["flexdoc-v4eq: Publish validated claims"]
    Publish --> Archive["flexdoc-9z3m: Archive and close"]
```

### Phase 1: Stabilize the 0.3.0 Contract and Release Gates

The merge baseline and three release-mechanics tasks can proceed in parallel.
The breaking API changes wait for PR #9 so their branches start from the normalized
source contract.

| Bead | Deliverable | Blocked By |
| --- | --- | --- |
| `flexdoc-lv8m` | Merge PR #9 and ratify normalized source coordinates; completed 2026-07-09 | None |
| `flexdoc-qire` | Reject context-free hints over duplicate quotes; completed 2026-07-09 | `flexdoc-lv8m` |
| `flexdoc-lcuh` | Group the eight pre-1.0 API cleanup beads; completed 2026-07-09 | `flexdoc-lv8m` establishes the baseline |
| `flexdoc-ltzx` | Make paragraph heading metadata properties; completed 2026-07-09 | `flexdoc-lv8m` |
| `flexdoc-ikm6` | Make recursive collection include inline descendants by default; completed 2026-07-09 | `flexdoc-lv8m` |
| `flexdoc-buw9` | Make cached structural views mutation-safe; completed 2026-07-09 | `flexdoc-lv8m` |
| `flexdoc-0cbm` | Rename the navigable-link form constant; completed 2026-07-09 | `flexdoc-lv8m` |
| `flexdoc-p60e` | Put resolution beside the public `SpanRef` API; completed 2026-07-09 | `flexdoc-qire` |
| `flexdoc-s85t` | Tier the `flexdoc.docs` export surface; completed 2026-07-09 | `flexdoc-lv8m` |
| `flexdoc-aaow` | Tolerate trailing horizontal whitespace on frontmatter delimiters; completed 2026-07-09 | `flexdoc-lv8m` |
| `flexdoc-uogy` | Share paragraph-size aggregation without a temporary `FlexDoc`; completed 2026-07-09 | `flexdoc-lv8m` |
| `flexdoc-pcac` | Refresh the supply-chain gate; completed 2026-07-09 with no exceptions or audit ignores | None |
| `flexdoc-ek6u` | Back the OS-independent classifier with representative macOS CI; completed 2026-07-09 | None |
| `flexdoc-44b1` | Harden and reproduce the tag-aware local release workflow; completed 2026-07-09 | None |
| `flexdoc-63p5` | Validate and publish 0.3.0; completed 2026-07-11 | Every preceding Phase 1 deliverable |

`TextUnit` is not in the API batch because its `StrEnum` conversion landed on PR #9. The
stale root-API beads `flexdoc-l0lc` and `flexdoc-bift` are also closed because their
implementation and contract tests already landed.

The structural cache decision is hybrid: `Block` graphs and their metadata are deeply
immutable and shared, while `sections()` recursively copies its tree because sections
contain deliberately editable `Paragraph` objects.
Both choices prevent public mutation from corrupting cached reads without freezing the
editing model.

### Phase 2: Add Source-Grounded AI Workflow Primitives

Phase 2 implementation begins after 0.3.0 publishes.
The native TextRef plan settles the shared reference, annotation-ownership, and context
rendering design before the remaining fragment, structure, normalized-matching, and
suggestion work. Its child-bead dependency graph lives in that focused plan; the table
below keeps only the Phase 2 sequencing boundary.

| Bead | Deliverable | Blocked By |
| --- | --- | --- |
| `flexdoc-4imy` | Implement native TextRef values, mapping, resolution, context, annotations, rendering, and validation through its child beads | `flexdoc-63p5` |
| `flexdoc-p6xv` | Define rendered-text URL fragment projection | `flexdoc-63p5` |
| `flexdoc-hc17` | Add structural text accessors and section outlines | `flexdoc-63p5` |
| `flexdoc-i229` | Add opt-in normalized re-anchoring with corpus evidence | `flexdoc-63p5` |
| `flexdoc-zdu2` | Define `SuggestedEdit` and atomic batch application | TextRef mapping, annotation, and resolution children of `flexdoc-4imy` |
| `flexdoc-vav2` | Validate AI workflows with runnable examples and compatibility tests | All preceding Phase 2 API beads |
| `flexdoc-f4mz` | Validate and publish 0.4.0 | `flexdoc-vav2` |

`flexdoc-z09f` evaluates fuzzy or edit-distance recovery only after `flexdoc-i229` has a
representative corpus.
It remains opt-in backlog work and does not block 0.4.0.

### Phase 3: Complete Extensions, Downstream Adoption, and Promotion

The synthetic layer can begin after 0.3.0. Promotion waits for both the released 0.4.0
workflow APIs and the Chopdiff migration.

| Bead | Deliverable | Blocked By |
| --- | --- | --- |
| `flexdoc-t5rh` | Implement the synthetic marker-tag layer | `flexdoc-63p5` |
| `flexdoc-19h2` | Migrate Chopdiff once to the released surface | `flexdoc-t5rh` |
| `flexdoc-b8a4` | Exercise annotation and chunking APIs downstream | `flexdoc-19h2`, `flexdoc-f4mz` |
| `flexdoc-v4eq` | Publish the validated introduction and public claims | `flexdoc-b8a4` |
| `flexdoc-9z3m` | Archive superseded plans and close the roadmap | `flexdoc-v4eq` |

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

1. Merge PR #9 after its branch tests and CI pass; completed 2026-07-09 without a
   0.2.x publication.
2. Complete Phase 1 and publish 0.3.0 with a migration-focused changelog; completed
   2026-07-11 (tag `v0.3.0`, GitHub Release, and PyPI publication via `release.yml`).
3. Complete Phase 2 behind the next `DocGraph` schema version and publish 0.4.0.
4. Complete Phase 3 only after downstream adoption validates the extension APIs.

## Resolved Phase 2 Decisions

- Consumers own annotations and pass them explicitly to FlexDoc for rendering or graph
  serialization; `FlexDoc` does not store mutable annotation state.
- `FlexDoc.graph()` without annotations preserves `DocGraph/v0.1`. Explicitly supplying
  annotations selects `DocGraph/v0.2`.
- TextRef identifies targets. Annotation bodies, workflow state, edit operations, and
  contextual views remain separate layers over it.

## References

- PR [#9](https://github.com/jlevy/flexdoc/pull/9)
- [2026-07 senior engineering review](../../review/senior-engineering-review-flexdoc-2026-07.md)
- [FlexDoc design specification](../../../flexdoc-spec.md)
- [Native TextRef integration plan](plan-2026-07-14-native-textref-integration.md)
- [TextRef research](../../research/research-2026-07-10-text-reference-microformat.md)
- [Initial post-review refinements plan](plan-2026-07-08-post-review-refinements.md)
- [Extraction plan](plan-2026-06-11-flexdoc-extraction.md)
- [W3C Web Annotation selectors](https://www.w3.org/TR/annotation-model/#selectors)
- [URL Fragment Text Directives](https://wicg.github.io/scroll-to-text-fragment/)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
