# Feature: Native TextRef Integration

**Date:** 2026-07-14 (last updated 2026-07-14)

**Author:** Joshua Levy and Codex

**Status:** Approved; implementation not started

## Overview

FlexDoc will make TextRef the portable reference for source-grounded document targets.
Any locatable paragraph, sentence, block, section, link, or node can produce a TextRef
through one document-bound API. The same reference can resolve to a concise URI, a
structured source context, or an annotation rendered beside that context.

The design stays layered:

- TextRef identifies a document and an optional target within its canonical source
- FlexDoc maps parsed objects to TextRefs and resolves them against a document snapshot
- Annotations and extracted values retain TextRefs without changing reference identity
- Context renderers combine resolved source and optional annotation bodies for people
  and language models

The protocol shape is deliberately small:

```text
TextRef = document + optional source_hash + optional selector
selector = span | point | section
```

Omitting the selector targets the whole document. Future selector kinds can extend the
union without changing these branches.

## Goals

- Map every locatable public FlexDoc object to a source-grounded TextRef
- Keep document identity and source hashing out of individual paragraph, section, and
  node objects
- Support whole-document, arbitrary span, zero-width point, and semantic section
  targets
- Preserve the existing `SpanRef` API while using it as span-selector evidence inside
  TextRef
- Provide strict JSON and canonical URI projections
- Return typed resolution results that distinguish missing, ambiguous, stale,
  unsupported, and boundary-mismatched targets
- Resolve references to structured source context with derived line and column labels
- Support small annotation envelopes and deterministic, text-friendly contextual views
- Let extraction, search, chunking, diagnostics, and language-model workflows retain
  one or more TextRefs as provenance
- Preserve `DocGraph/v0.1` and introduce typed annotations only through an explicit
  `DocGraph/v0.2` path

## Non-Goals

- Network, filesystem, Git, authentication, or cache policy in the TextRef core
- A general annotation platform with permissions, collaboration, or workflow engines
- Fuzzy matching in the initial implementation
- CRDT, DOM, PDF, rendered-text, or media selectors
- Table-, row-, cell-, heading-, list-item-, or code-block-specific selector kinds
- A discontinuous selector; consumers may retain several TextRefs
- A round-trippable contextual rendering
- Automatic application of suggested edits without a separate validated edit profile
- A standalone TextRef package before a second-language consumer needs it

## Background

FlexDoc already retains one LF-normalized Unicode source string and exposes code-point
spans across its textual, Markdown, and document views. `SpanRef` adds quote-based
recovery, but it assumes that the caller already has the correct source and collapses
missing and ambiguous outcomes into `None`. Parsed objects also expose spans through
different attributes and do not know the source document's locator.

The TextRef research composes a DocRef locator, optional canonical-source hash, and
typed selector. This plan adopts that composition inside FlexDoc and adds the narrow
adapter and rendering surfaces required by concrete clients.

## Tracking

- `flexdoc-4imy`: implementation epic for this specification
- `flexdoc-6582`: parent Phase 2 and 0.4.0 release epic

| Order | Bead | Implementation slice | Blocked by |
| --- | --- | --- | --- |
| 1 | `flexdoc-7yos` | Core models, validation, JSON/schema, and URI codec | None |
| 2 | `flexdoc-rbvu` | Typed exact span, point, and section resolution | `flexdoc-7yos` |
| 3 | `flexdoc-gupc` | `TextRefContext` and FlexDoc target adapters | `flexdoc-rbvu` |
| 4a | `flexdoc-qw7n` | Structured source context and display coordinates | `flexdoc-gupc` |
| 4b | `flexdoc-jl5b` | Annotation profile, sidecar, and `DocGraph/v0.2` | `flexdoc-7yos` |
| 5 | `flexdoc-ktl3` | Deterministic TextRef and annotation rendering | `flexdoc-qw7n`, `flexdoc-jl5b` |
| 6 | `flexdoc-1nex` | Workflow examples, goldens, and compatibility validation | `flexdoc-ktl3` |

Steps 4a and 4b can proceed in parallel. Each bead includes its focused tests and
documentation; the final bead supplies cross-format and end-to-end validation rather
than postponing basic testing until the end.

## Design

### Core Values

The public reference vocabulary is:

- `DocRef`: validated document locator and provenance
- `SpanRef`: exact quote, immediate context, and optional code-point position evidence
- `TextRef`: document, optional source hash, and optional typed selector
- `TextRefTargetKind`: `whole_document`, `span`, `point`, or `section`
- `TextRefResolution`: typed document, source-validation, selector, method, span, and
  candidate results

The selector is a strict discriminated union. Point and section branches may use
module-level typed models, but they do not need separate top-level reference concepts.
Core values are immutable. Serialization uses strict models and rejects unknown fields;
consumer extensions live in a namespaced `extensions` object.

FlexDoc-generated TextRefs include an algorithm-qualified source hash and retain their
position hint by default. The source quote remains the durable recovery evidence after
the source changes.

### Document-Bound Reference Context

`FlexDoc.references()` binds one document locator and one source snapshot:

```python
refs = doc.references(document="./design.md")

paragraph_ref = refs.for_target(doc.paragraphs[0])
section_ref = refs.for_target(doc.sections()[0])
node_ref = refs.for_target(doc.collect(kinds={NodeKind.link})[0])

whole_ref = refs.whole_document()
span_ref = refs.for_span(start, end)
point_ref = refs.for_point(position, affinity="after")
```

The returned `TextRefContext` computes the canonical source hash once and supplies:

- `for_target(value)` for supported FlexDoc values
- `whole_document()`, `for_span()`, `for_point()`, and `for_section()` constructors
- `resolve(ref)` for typed resolution against the bound document
- `context(ref, ...)` for structured excerpts and display coordinates
- `render_context(ref, ...)` and `render_annotations(...)` as derived views

TextRefs are derived on demand rather than stored on parsed objects. This avoids
duplicating document and hash fields, prevents stale materialized references, and keeps
copied or edited paragraph and section values independent from reference ownership.

### Mapping FlexDoc Values

`for_target()` uses one central adapter table:

| Value | Selector |
| --- | --- |
| `Paragraph`, `Sentence`, `Block`, `BaseBlock`, located `Link`, ordinary `Node` | Span over the complete source range |
| `Section` or document-layer section `Node` | Section selector anchored by its heading and optional following boundary heading |
| Explicit `(start, end)` range | Span |
| Explicit boundary | Point with affinity |
| Complete document | No selector |

A heading alone, table, row, cell, list item, code block, or other parsed object uses a
span in the initial format. A complete heading-owned section uses the semantic section
selector so edits inside the section do not invalidate its identity.

Unlocatable values such as a `Node` with `source_span=None` fail construction visibly.
Node IDs, line numbers, and parser-object identities are never persisted as the only
target evidence.

### Resolution and Context

Resolution keeps independent facts instead of one nullable result:

| Axis | Values |
| --- | --- |
| Document | `resolved`, `unavailable`, `invalid` |
| Source validation | `absent`, `matched`, `mismatched` |
| Selector | `whole_document`, `resolved`, `missing`, `ambiguous`, `boundary_mismatched`, `unsupported` |
| Method | `source_position`, `context_position`, `exact_quote`, `context_quote`, `point_context`, `point_affinity`, `section_structure`, `section_anchors`, `none` |

The exact resolver uses a matching source hash plus position first, then corroborated
position, unique quote, and contextual disambiguation. It never chooses an arbitrary
duplicate. Point selectors resolve boundaries through source-bound positions and
two-sided or affinity-owned context. Section selectors resolve their heading anchors
and derive the current range from FlexDoc's section hierarchy.

`context()` returns a structured value containing the resolved span, selected source,
surrounding source lines, one-based line and code-point-column labels, resolution
method, and source-validation state. Line labels are derived presentation, not durable
selector identity.

### Annotation and Context Rendering

TextRef answers where; an annotation envelope answers what is said or proposed there.
The initial envelope contains:

- Independent annotation ID
- One TextRef target
- One or more motivations
- Optional discriminated plain-text body
- Optional style, tags, `captured_text`, and import provenance

Workflow status, target-resolution state, history, edit operations, and synchronization
metadata remain outside TextRef. Several annotations may share one target. Consumers
that need several targets retain several TextRefs rather than inventing a discontinuous
selector.

A one-document annotation set may hoist `document` and `source_hash` and store bare
selectors. It expands each target to a complete TextRef before validation or resolution.
Annotations remain consumer-owned and are passed to FlexDoc for serialization or
rendering; `FlexDoc` does not store them as mutable document state.

The deterministic context renderer emits Markdown-compatible ASCII with:

- Document and source-validation metadata
- Merged line-numbered context windows
- Stable annotation IDs and target kinds
- Complete bounded quotes, explicit elision, and point affinity
- Annotation bodies adjacent to their resolved source
- Separate missing, ambiguous, unsupported, and orphaned sections

The structured TextRef or annotation set remains authoritative. Rendered context is
regenerated and is never parsed back into records.

### Serialization and DocGraph

JSON is the normative TextRef value model. A canonical `textref:0.1?...` URI is a
reversible projection of one TextRef and never carries an annotation body. Restricted
YAML is available for concise one-document annotation sets.

`FlexDoc.graph()` without annotations keeps its current `DocGraph/v0.1` behavior.
Passing annotations explicitly selects `DocGraph/v0.2`, whose source context supplies
the document and source hash for embedded bare selectors. Detached annotations retain
complete TextRefs.

`SpanRef.to_text_fragment()` remains compatible in the 0.4 release. New browser
navigation work uses an explicit rendered-text adapter and refusal rules rather than
treating Markdown source as rendered page text.

### Extraction and Other Consumers

FlexDoc does not prescribe one extraction-result model. A result or field may retain a
`TextRef` or `tuple[TextRef, ...]` under a consumer-owned `source_refs` field. The same
composition supports chunks, search results, diagnostics, citations, summaries,
classifications, redactions, review comments, and suggested-edit envelopes.

## Compatibility Requirements

- **Library APIs:** Additive for 0.4. Existing `SpanRef` construction, resolution, and
  text-fragment methods remain available.
- **Serialized formats:** `DocGraph/v0.1` retains its meaning. TextRef and
  `DocGraph/v0.2` are new strict formats with explicit version fields.
- **Source coordinates:** Continue using normalized Unicode code-point offsets.
- **Annotation state:** No migration because the reserved v0.1 annotation list has no
  defined populated schema.
- **Dependencies:** Add none for the protocol or rendering core.

## Implementation Plan

### Phase 1: TextRef Core and FlexDoc Mapping

- [x] `flexdoc-7yos`: implement strict DocRef, source-hash, selector, TextRef, JSON,
  schema, and URI values with conformance fixtures
- [x] `flexdoc-rbvu`: implement typed exact resolution for span, point, and section
  selectors while preserving `SpanRef.resolve()`
- [x] `flexdoc-gupc`: add `FlexDoc.references()` and adapters for every locatable public
  value, including visible unlocatable and cross-document failures

### Phase 2: Context, Annotations, and Integration

- [x] `flexdoc-qw7n`: add bounded structured source context and derived line/column
  labels for every resolution outcome
- [x] `flexdoc-jl5b`: add the consumer-owned annotation profile, one-document sidecar,
  and explicit `DocGraph/v0.2` path while preserving v0.1
- [x] `flexdoc-ktl3`: add deterministic single-reference and batch annotation context
  rendering with explicit elision and unresolved groups
- [ ] `flexdoc-1nex`: add cross-format goldens and runnable extraction, retrieval,
  annotation, citation, and edit-target workflows

## Testing Strategy

- Use red-green-refactor for each constructor, resolution outcome, and serialization
  branch
- Keep focused behavior tests for mappings, strict validation, source hashes, Unicode
  coordinates, points, sections, ambiguity, and unsupported targets
- Use shared JSON fixtures for canonical wire and URI round trips
- Use the document golden corpus for cross-view source-span-to-TextRef invariants
- Golden-test contextual views, merged windows, explicit elision, and unresolved groups
- Preserve root-export and `DocGraph/v0.1` compatibility tests
- Run `make lint` and `make test` after each implementation slice

## Rollout Plan

1. Land the core types and FlexDoc reference context without populating annotations.
2. Land contextual rendering, the annotation profile, and `DocGraph/v0.2` behind
   explicit APIs.
3. Validate the complete workflows through runnable examples before publishing 0.4.0.
4. Extract a standalone package only when a TypeScript or other second-language
   consumer requires the persisted format.

## Open Questions

The main architecture is settled. Implementation must still choose bounded defaults
for quote/context sizes, URI limits, and contextual-rendering budgets. Those values
require fixtures and should remain named policy constants rather than wire-format
semantics.

## References

- [FlexDoc design specification](../../../flexdoc-spec.md)
- [TextRef research](../../research/research-2026-07-10-text-reference-microformat.md)
- [Stabilization roadmap](plan-2026-07-09-flexdoc-stabilization-roadmap.md)
- [Span-reference research](../../research/research-2026-05-30-span-references.md)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
