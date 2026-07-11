# Research: A Portable DocRef, SpanRef, and TextRef Microformat

**Date:** 2026-07-10 (last updated 2026-07-10)

**Author:** Codex, synthesizing existing FlexDoc and tbd design work

**Status:** Complete (proposal for review)

## Overview

tbd and FlexDoc each solve one half of the same reference problem:

- tbd's **DocRef** locates a document and records where it came from
- FlexDoc's **SpanRef** identifies a passage within source text and can recover that
  passage after offsets move

Neither type alone is a portable reference to a passage. A DocRef does not identify an
exact representation or select text. A SpanRef assumes the caller already has the
correct source text. Cross-repository reviews, durable citations, annotations, and
source-grounded edits need all three of the following:

1. A document locator
2. An exact or verifiable source snapshot
3. A selector within that source

This research evaluates whether these concerns should become a small standalone
protocol with Python and TypeScript implementations. The proposed abstraction is
**TextRef**, a compact composition of DocRef, SnapshotRef, and SpanRef:

```text
TextRef
├── DocRef       requested document locator and provenance
├── SnapshotRef  normalized-text identity and optional resolved revision
└── SpanRef      optional passage selector within that text
```

The recommendation is to create one language-neutral specification and conformance
suite in a standalone repository, with thin Python and TypeScript reference
implementations. The core should be pure and dependency-free. Filesystem, network,
Git, rendering, and application policy should remain in consumer-owned adapters.

## Questions to Answer

1. What problem should the shared reference protocol solve, and which adjacent
   problems should remain outside it?
2. How do tbd's DocRef and FlexDoc's SpanRef currently behave?
3. Which parts of their behavior are stable contracts, implementation policies, or
   unresolved gaps?
4. What relevant standards and existing formats should be reused or avoided?
5. Should the portable form be a URI-like string, a structured object, or both?
6. How should document location, snapshot identity, and passage selection compose?
7. What semantics must be identical across Python and TypeScript?
8. Which decisions require further design or empirical validation before extraction?

## Scope

Included:

- Unicode source documents, initially Markdown and other decoded text
- Local, application-internal, URL, GitHub, and GitLab document locators
- Reproducible normalized-text snapshots
- Durable exact-text selectors with contextual and positional evidence
- A normative JSON data model with an optional restricted YAML projection
- Pure Python and TypeScript APIs
- Deterministic validation, normalization, equality, and resolution behavior
- Migration paths for tbd and FlexDoc

Excluded from the initial protocol:

- Annotation bodies, authorship, motivations, permissions, or workflow state
- Applying edits or resolving edit conflicts
- Fetching, authentication, caching, redirects, or repository checkout
- Markdown rendering and source-to-rendered-text mapping
- DOM, XPath, PDF geometry, OCR, media, or binary selectors
- CRDT anchors and live collaborative editing
- A normative fuzzy-matching algorithm
- A universal document graph or parser model

These exclusions keep the protocol useful without turning it into a document platform.

## Terminology

- **DocRef:** A compact application reference that says where a document can be found.
  It is a requested locator and provenance record, not necessarily immutable identity.
- **SnapshotRef:** Evidence identifying one normalized source-text representation.
- **SpanRef:** A selector for one non-empty passage in already-available normalized
  source text.
- **TextRef:** A DocRef with an optional SnapshotRef and optional SpanRef. Without a
  SpanRef it refers to the whole document.
- **Resolver:** Consumer-provided code that obtains text and provenance for a DocRef.
- **Canonical source text:** The precisely normalized Unicode string against which
  snapshot hashes and SpanRef offsets are computed.

The word *reference* is intentional. A reference may need contextual resolution and
can fail. It is not necessarily a globally unique or permanently dereferenceable
identifier.

## Findings

### DocRef Is a Locator and Provenance Primitive

tbd DocRef v0.1 is a strict, single-string application grammar with these forms:

| Kind | Example | Resolution Context |
| --- | --- | --- |
| Internal | `internal:guidelines/python-rules.md` | Consuming application's bundled documents |
| Local | `./docs/design.md` | Explicit caller-supplied filesystem base |
| Absolute local | `/srv/docs/design.md` | Host filesystem |
| URL | `https://example.com/design.md` | URL resolver |
| Git | `github:owner/repo@main//docs/design.md` | Git host and repository |

The grammar rejects bare relative paths, home-relative paths, and unknown schemes.
GitHub and GitLab file URLs normalize to provider-prefixed Git forms. The `//`
separator between Git revision and path permits revisions containing slashes.

The DocRef v0.1 document specifies syntactic equality after normalization, with one
additional local-path rule that ignores a single leading `./`. It does not claim that
two paths, URLs, branches, or provider spellings resolve to the same bytes. This
distinction is necessary: a branch DocRef can remain the same while its content changes.

tbd currently uses DocRefs for:

- `docs_cache.files` source locations
- managed-document fork provenance
- generated docmap source fields
- `tbd docs add` inputs

tbd's managed-document identity remains `kind + name`; DocRef records location and
provenance. Its issue `spec_path` also remains a deliberately simpler repo-relative
path. Neither should be redefined as TextRef merely because TextRef exists.

Current implementation details reveal work that extraction would need to finish:

- The source map contains parsing, formatting, normalization, and equality logic, but
  the installed package exposes no supported public DocRef API. Its internal bundled
  chunk does not export the formatter or equality helper, and normalization alone does
  not implement the documented leading-`./` equality rule.
- `tbd docs add` requires an explicit Git revision even though the base grammar permits
  an omitted revision. This consumer-level restriction improves reproducibility but a
  branch revision remains mutable.
- DocRef validation is not applied uniformly at every configuration boundary.
- Git resolution can discover a commit, but tbd v0.3.0 does not persist that result as
  a general snapshot record.
- Fork manifests store an LF-normalized SHA-256 base hash. Their schema permits a source
  revision, but the current fork path does not populate it.
- Git fragments are parsed and preserved, URL fragments remain embedded in the URL, and
  `#` remains path text for local and internal references. None is resolved to document
  content.
- Internal and relative-local forms are contextual, not globally portable.

DocRef is therefore suitable for extraction, but extraction is partly specification
work rather than a mechanical package move.

### SpanRef Is a Durable Selector Over Supplied Text

FlexDoc's current SpanRef has this shape:

```yaml
exact: Canonical source is authoritative.
prefix: "The parser guarantees that "
suffix: " Derived views are secondary."
start: 1842
end: 1876
```

Its contract is:

- `exact` is the durable quoted passage
- `prefix` and `suffix` are optional immediate context
- `start` and `end` are optional zero-based, start-inclusive, end-exclusive Unicode
  code-point offsets
- Offsets are hints unless tied to known source identity
- Resolution verifies an offset when context corroborates it, then searches for exact
  occurrences and uses context to disambiguate duplicates
- Missing and ambiguous references currently both return `None`
- Persistence drops offsets by default
- Exact matching is case-sensitive and whitespace-sensitive
- Approximate matching is deferred

FlexDoc normalizes CRLF and lone CR line endings to LF. `DocGraph.SourceInfo.sha256` is
the SHA-256 digest of that normalized text encoded as UTF-8. No Unicode, whitespace,
BOM, or final-newline normalization is applied.

Several implementation choices should not silently become protocol rules:

- The constructor currently captures 24 code points of context on each side.
- `from_node()` depends on a FlexDoc Node and belongs in a FlexDoc adapter.
- Empty quotes and malformed coordinate pairs can be constructed but do not resolve
  meaningfully.
- Partial context scoring is useful recovery policy but needs explicit cross-language
  semantics if it is standardized.
- Mutation through `resolve_and_update()` may be less suitable than immutable value
  objects in a small protocol package.

### Snapshot Identity Connects DocRef and SpanRef

DocRef and SpanRef become coherent when a snapshot record sits between them:

```text
DocRef ──resolve──> normalized source + SnapshotRef ──select──> SpanRef result
```

This resolves a subtle ambiguity in the current SpanRef contract. A context-free offset
cannot safely choose between duplicate quotes when the caller supplies an unverified
document. If the TextRef's snapshot hash matches the supplied normalized text, however,
the offset belongs to that exact snapshot and can identify the intended duplicate.

The resulting rule is:

- When the snapshot hash matches, a valid offset whose slice equals `exact` is
  authoritative for that snapshot.
- When the snapshot is absent or differs, the offset is only a hint and quote/context
  re-anchoring remains conservative.

Snapshot-bound TextRefs should therefore normally retain offsets. Dropping them loses
useful identity within an immutable snapshot. The quote remains necessary for recovery
after the document changes.

### Source Text and Rendered Text Are Different Representations

FlexDoc SpanRefs select normalized source Markdown. Browser URL Text Fragments select
rendered page text. A Markdown source quote such as `**important**` does not identify
the same character stream as the visible word `important`.

TextRef v0.1 should define only canonical source text. Browser fragments, rendered
Markdown selectors, DOM ranges, and extracted PDF text should use explicit adapters or
future representation profiles. A resolver must never silently reinterpret a
source-text SpanRef against rendered text.

### Cross-Language Semantics Require More Than Matching Data Classes

Python indexes strings by Unicode code points in normal cases. JavaScript indexes
strings by UTF-16 code units. The same integer therefore selects different content
after many non-BMP characters unless TypeScript converts explicitly.

A shared protocol must also settle:

- Unpaired surrogate handling
- Newline normalization
- Digest input and encoding
- Half-open interval semantics
- Duplicate-quote behavior
- Context construction and comparison
- Safe integer limits in JSON
- Unknown-field behavior

JSON Schema can validate structure but cannot define these algorithms. Normative prose
and shared golden vectors are both required.

## Relevant Standards and Prior Art

### W3C Web Annotation Provides the Best Conceptual Model

The W3C Web Annotation Data Model represents a selected resource as:

- `source`: the resource
- `state`: the intended representation of that resource
- `selector`: a segment within that representation

This maps directly to DocRef, SnapshotRef, and SpanRef. Its TextQuoteSelector supplies
`exact`, `prefix`, and `suffix`; its TextPositionSelector supplies zero-based half-open
positions. It explicitly requires Unicode code points, logical text order, and advises
against splitting grapheme clusters.

The full Web Annotation JSON-LD/RDF model also covers bodies, motivations, agents,
styles, multiple resources, states, and protocol concerns. Adopting all of it would make
the common low-level reference harder to embed. TextRef should be a small compatible
profile, with a documented mapping to Web Annotation rather than a dependency on its
full representation.

### Generic URI Fragments Are the Wrong Extension Point

RFC 3986 defines a fragment as a client-resolved secondary-resource identifier whose
semantics depend on the retrieved media type. RFC 8820 consequently warns applications
not to impose a generic fragment grammar across media types they do not control.

This argues against forms such as:

```text
github:owner/repo@main//docs/design.md#span=<encoded-selector>
```

Such a string conflates document retrieval and passage selection, requires difficult
escaping, and creates inconsistent behavior across Markdown source, rendered HTML,
local files, and provider URLs.

tbd may continue accepting fragments in standalone DocRefs for compatibility and
presentation. TextRef should prevent a recognized Git or URL fragment from competing
with `span`, so one object never contains two authoritative passage selectors. Before
this becomes a schema rule, DocRef must define fragment extraction for each kind. In
particular, `#` can be valid path text in local and internal references.

### Browser Text Fragments Are an Export Format

The WICG `#:~:text=` format also uses quote and context, but it is a browser-navigation
draft rather than a W3C Standard. Its rendered-DOM, whitespace, word-boundary,
first-match, and security behavior differs from exact source matching.

It is useful as an explicit projection from an appropriate rendered-text selector. It
should not define TextRef persistence or resolution semantics.

### Offset and Content-Addressed Formats Solve Narrower Problems

- **RFC 5147** identifies character or line positions in `text/plain` and can attach
  integrity information. It detects change but does not recover from edits. Its MD5,
  clamping, and fragment syntax should not be inherited.
- **Package URL (purl)** identifies packages, versions, qualifiers, and package-relative
  subpaths. A document is not generally a package, and passages are not package
  subpaths.
- **Software Heritage identifiers (SWHIDs)** provide strong content-addressed source
  identities with origin, revision, path, and line qualifiers. They are valuable for
  archived software citations but do not cover application-internal, local, or general
  URL documents, and line selectors remain edit-fragile.
- **RFC 6920 `ni` identifiers** name content by algorithm-qualified digest but do not
  locate a mutable document or define TextRef's normalized-text digest input.

These formats reinforce the distinction between location, content identity, and
selection. None replaces the proposed composition.

## Design Requirements

The protocol should meet these requirements:

1. **Small:** Four value types, one compact JSON shape, and a narrow pure API.
2. **Composable:** Whole-document references and passage references use the same top
   level.
3. **Source-grounded:** v0.1 selects one precisely defined Unicode source stream.
4. **Reproducible:** A snapshot digest can verify the exact selector coordinate space.
5. **Durable:** Quotes and context can recover passages after positions move.
6. **Conservative:** Ambiguity is reported rather than guessed.
7. **Cross-language:** Python and TypeScript produce identical normalized forms,
   digests, offsets, and outcomes.
8. **Human-usable:** DocRefs remain compact strings; TextRefs remain readable JSON or
   YAML.
9. **I/O-independent:** Parsing and selection do not perform filesystem or network
   access.
10. **Extensible without looseness:** Versioned schemas distinguish supported evolution
    from misspelled fields.

## Comparison Matrix

| Approach | Compact | Cross-Tool | Snapshot-Aware | Durable Passage | I/O-Independent | Main Problem |
| --- | --- | --- | --- | --- | --- | --- |
| Keep types inside tbd and FlexDoc | Yes | No | Partial | Partial | Yes | Semantics and fixes drift |
| Adopt full W3C Web Annotation | No | Yes | Via states | Yes | Yes | Too broad and JSON-LD-heavy |
| Encode everything in a URI/fragment | Superficially | Limited | Awkward | Awkward | Yes | Media-type conflicts and escaping |
| Use only content-addressed identifiers | Moderate | Yes | Yes | No | Usually | Cannot locate mutable/current sources or re-anchor passages |
| Standalone focused TextRef protocol | Yes | Yes | Yes | Yes | Yes | Requires a new maintained contract |

## Options Considered

### Option A: Keep DocRef and SpanRef in Their Current Projects

**Description:** tbd owns DocRef, FlexDoc owns SpanRef, and applications compose them
ad hoc.

**Advantages:**

- No new repository or release process
- Minimal immediate migration
- Each project can evolve independently

**Disadvantages:**

- No shared snapshot or top-level reference contract
- TypeScript and Python behavior can diverge
- tbd cannot reuse SpanRef without depending on a larger Python document library
- FlexDoc would need to duplicate or depend on tbd's TypeScript-specific DocRef logic
- Cross-tool persisted references have no independent owner

This remains reasonable only if the two systems never exchange references. Their
planned annotation, review, and source-grounded editing work makes that unlikely.

### Option B: Adopt W3C Web Annotation Directly

**Description:** Persist complete `SpecificResource`, state, and selector JSON-LD.

**Advantages:**

- Mature conceptual model and vocabulary
- Existing selector and representation-state semantics
- Interoperability with annotation systems

**Disadvantages:**

- Larger object model than tbd or FlexDoc needs
- JSON-LD/RDF context and vocabulary increase implementation surface
- Does not define the DocRef locator grammar
- Its text normalization leaves application-specific work
- Full annotations conflate targeting with bodies and workflow concerns

The concepts should be reused, but the complete format should not be required.

### Option C: Define a Single TextRef URI

**Description:** Encode document, snapshot, and passage into one string.

**Advantages:**

- Easy to paste into text fields
- Superficially resembles familiar links
- Could serve as a command-line interchange form

**Disadvantages:**

- Quotes and context require extensive escaping
- Generic fragment semantics conflict with URI and media-type rules
- Optional fields and future selectors make the grammar difficult to evolve
- Long selections produce long, opaque strings
- Human editing becomes less reliable than structured JSON or YAML

A compact string projection could be added after the object model stabilizes. It should
not be the normative v0.1 representation.

### Option D: Make Content Hashes the Primary Identifier

**Description:** Refer to normalized text by digest and treat locations as optional
hints.

**Advantages:**

- Immutable snapshot identity
- Straightforward integrity verification
- Deduplication across locations

**Disadvantages:**

- A hash does not say where content can be retrieved
- Current or mutable documents remain important user concepts
- Hash-only references cannot recover a passage in a later version
- Local and internal workflows would need separate locator metadata anyway

Content hashes belong in SnapshotRef, not in place of DocRef.

### Option E: Create a Focused Standalone TextRef Protocol

**Description:** Define DocRef, SnapshotRef, SpanRef, and TextRef in one small protocol
repository with shared fixtures and Python and TypeScript implementations.

**Advantages:**

- Clean semantic ownership
- No runtime dependency between tbd and FlexDoc
- One cross-language behavior contract
- Reusable by reviews, annotations, citations, edits, and other tools
- Small enough to remain understandable and dependency-free

**Disadvantages:**

- Adds release and compatibility responsibilities
- Requires migrations in two projects
- Forces unresolved edge cases to be decided explicitly

This is the recommended approach.

## Proposed Design

### Protocol Types

The public vocabulary should be:

- `DocRef`: requested document locator
- `SnapshotRef`: normalized source identity
- `SpanRef`: passage selector over supplied normalized text
- `TextRef`: whole-document or passage reference

`TextRef` is preferable to `DocumentTarget` because it is concise and states the
representation boundary: v0.1 refers to text, not arbitrary binary resources or
rendered layout.

### Persisted Shape

```json
{
  "format": "textref/0.1",
  "document": "github:owner/repo@main//docs/design.md",
  "snapshot": {
    "text_profile": "textref-source-v1",
    "text_hash": "sha256:83f6d4...",
    "revision": "9f82c1a..."
  },
  "span": {
    "exact": "Canonical source is authoritative.",
    "prefix": "The parser guarantees that ",
    "suffix": " Derived views are secondary.",
    "start": 1842,
    "end": 1876
  }
}
```

Rules proposed for v0.1:

- `format` and `document` are required.
- `snapshot` is optional. If present, `text_profile` and `text_hash` are required and
  `revision` is optional.
- `span` is optional. Its absence means the whole document.
- A TextRef containing `span` has no independently recognized Git or URL fragment. The
  final DocRef rules must define this per kind before it is enforced.
- `exact` is required and contains at least one Unicode code point.
- `prefix` and `suffix` are optional, non-empty immediate context strings.
- `start` and `end` are both present or both absent.
- Positions are non-negative JSON-safe integers, use Unicode code points, and form a
  start-inclusive, end-exclusive interval.
- When positions are present, `end - start` equals the code-point length of `exact`.
- The provisional recommendation is to reject unknown top-level fields while allowing
  future optional data under a defined, namespaced extension container. The final rule
  remains an explicit compatibility decision.

The optional fields form four useful reference profiles:

| Snapshot | Span | Meaning |
| --- | --- | --- |
| Absent | Absent | Floating reference to the whole document |
| Present | Absent | Reproducible reference to the whole snapshot |
| Absent | Present | Passage that can re-anchor in the currently resolved document |
| Present | Present | Reproducible passage with recovery behavior after the snapshot changes |

The JSON object is the normative persisted data model and is encoded as UTF-8. YAML is
only a convenience projection: it must use string keys and JSON-compatible values,
reject duplicate keys and custom tags, and deserialize to the same JSON value tree
before schema validation. YAML-specific scalar types or independent semantics are not
part of the protocol.

### Canonical Source Profile

The core resolver accepts a Unicode string; byte decoding is an adapter responsibility.
Every snapshot names the profile used to compute its hash. The proposed
`textref-source-v1` profile is:

1. Require Unicode scalar values and reject unpaired surrogates.
2. Convert CRLF and lone CR to LF.
3. Preserve all other code points exactly.
4. Do not normalize Unicode, case, whitespace, BOM, or final newlines.
5. Compute `text_hash` over the normalized string encoded as UTF-8.

Under this proposal, a BOM is retained as text, NEL/U+2028/U+2029 are not treated as
line endings, and the presence or absence of a final newline is preserved. Before v0.1,
these compatibility choices should be confirmed because changing any of them changes
offsets and hashes. Byte-oriented adapters must separately define their accepted
encodings and decoding failures.

The digest string should include its algorithm. RFC 6920 can inform equality, but the
field should be named `text_hash`, not HTTP `Content-Digest` or `Repr-Digest`, because
its input is an application-normalized source string. Snapshot identity is the tuple of
text profile, digest algorithm, digest length, and digest value; `revision` is resolver
provenance unless the final specification explicitly gives it stronger semantics.

### Resolution Semantics

Resolution separates document acquisition from passage selection:

1. Parse and normalize the DocRef without I/O.
2. Ask a consumer-owned resolver for decoded source text and provenance.
3. Apply the canonical source profile and compute the actual text hash.
4. Compare the expected and actual snapshot.
5. Resolve the SpanRef, if present.
6. Return a typed result containing the snapshot status, selection outcome, and method.

Recommended exact-selection tiers:

1. **Snapshot-bound position:** If hashes match and `[start, end)` equals `exact`, accept
   the position even when the quote occurs elsewhere.
2. **Corroborated position:** Without a matching hash, accept a position only when the
   quote and non-empty captured context corroborate it.
3. **Exact quote search:** Resolve a unique exact occurrence.
4. **Context disambiguation:** Resolve one duplicate only when context uniquely
   identifies it.
5. **Visible failure:** Report missing or ambiguous rather than choosing arbitrarily.

Approximate, case-normalized, or whitespace-normalized matching should be an optional
strategy with a named method and score. It should not change exact v0.1 behavior.

The result should keep independent axes rather than flattening a stale but successfully
re-anchored reference into one status:

| Axis | Suggested Values |
| --- | --- |
| Document | `resolved`, `unavailable`, `invalid` |
| Snapshot | `absent`, `matched`, `mismatched` |
| Span | `whole_document`, `resolved`, `missing`, `ambiguous` |
| Method | `snapshot_position`, `context_position`, `exact_quote`, `context_quote`, `none` |

A convenience nullable API may wrap these results, but persisted tools and edit
workflows need the distinctions. A `resolve_all` API can expose candidates while
`resolve_one` preserves conservative single-target semantics.

Snapshot mismatch policy depends on the operation:

- A citation or annotation viewer may re-anchor against current content while reporting
  that the snapshot changed.
- A source edit should normally require the expected snapshot or explicit stale-edit
  handling.

The protocol should expose the facts and selectable policy, not silently choose one
behavior for every consumer.

### Core and Adapter Boundary

The standalone core should provide:

- DocRef parsing, formatting, normalization, validation, and structural equality
- TextRef, SnapshotRef, and SpanRef validation and serialization
- Canonical source normalization and hashing
- SpanRef construction from a string and offsets
- Exact resolution over caller-supplied text
- Code-point and UTF-16 offset conversion
- Typed resolution results

The core should not provide:

- Filesystem or network access
- GitHub or GitLab authentication
- Redirect, cache, or credential policy
- Markdown rendering
- FlexDoc Node adapters
- Annotation or edit models

Resolvers must separately enforce filesystem roots, allowed schemes and hosts,
redirect limits, response-size limits, timeouts, and credential handling. Keeping I/O
outside the core reduces both dependencies and security exposure.

### Repository and Conformance Layout

A standalone repository such as `textrefs` should contain one specification and two
implementations:

```text
textrefs/
├── spec/
│   ├── docref.md
│   ├── snapshotref.md
│   ├── spanref.md
│   ├── textref.md
│   └── schemas/
├── fixtures/
│   ├── docref.jsonl
│   ├── normalization.jsonl
│   ├── hashing.jsonl
│   ├── span-resolution.jsonl
│   └── textref-validation.jsonl
├── python/
└── typescript/
```

The Markdown specifications are normative. JSON Schema validates structure. Shared
fixtures define examples and algorithm outcomes. Neither language implementation is
the specification for the other.

Conformance vectors should include:

- Every DocRef kind and invalid boundary
- Git revisions containing slashes
- Windows and POSIX paths
- URL and fragment normalization
- CRLF, CR, and LF equivalence
- Astral code points and UTF-16 conversion
- Combining marks, grapheme clusters, and bidirectional text
- Rejected unpaired surrogates
- Duplicate and overlapping quote occurrences
- Context ties and document-boundary context
- Matching, absent, and stale snapshots
- Maximum JSON-safe offsets
- Unknown and duplicate JSON members

### Integration With tbd

tbd should use the TypeScript package for its existing DocRef boundaries first. That
integration should:

- Preserve the current DocRef v0.1 spelling where deliberately compatible
- Export and test the public parser, formatter, normalizer, and equality API
- Validate every DocRef-bearing configuration field consistently
- Fix local absolute-path resolution as a consumer issue
- Keep `spec_path` and managed-document `kind + name` identity unchanged
- Add SnapshotRef only where resolved provenance or reproducibility is needed
- Add TextRef only to fields that actually target passages, such as future review
  findings or source citations

Managed-doc caching does not need a SpanRef. Whole-document features should continue
using DocRef or TextRef without `span`.

### Integration With FlexDoc

FlexDoc should use the Python package for SpanRef and snapshot primitives while keeping
FlexDoc-specific adapters locally:

- Keep `SpanRef.from_node()` in FlexDoc
- Re-export the standalone SpanRef only after deciding API and pickle compatibility
- Preserve `DocGraph/v0.1`
- Add document locator, snapshot, and typed annotation targets in an explicit later
  schema version
- Use bare SpanRef for annotations embedded in a DocGraph whose enclosing source already
  supplies document and snapshot context
- Use complete TextRef for annotations detached from a graph or targeting another
  document

The protocol decision should precede Phase 2 work on annotation ownership, batch
resolution, and snapshot-aware suggested edits. Rendered browser fragments remain a
separate FlexDoc adapter concern.

## Key Open Questions and Decision Points

### Document Location and Portability

1. **Application syntax or URI:** Should `github:` and `gitlab:` remain explicitly
   application-defined DocRef forms, or should Git locations become structured objects?
   They are not registered URI schemes.
2. **Portable profile:** Should portable persisted TextRefs reject `internal:` and local
   DocRefs, or permit them with an explicit resolver namespace/base?
3. **Git hosts:** Should v0.1 remain GitHub/GitLab-specific or define a generic host
   form without overgeneralizing forge behavior?
4. **Fragment migration:** Should existing DocRef fragments remain opaque, be split into
   a presentation field, or be rejected only when `span` is present?
5. **Equality:** The protocol needs separate names for structural DocRef equality,
   matching snapshot identity, and two locators resolving to the same target.

### Snapshot and Canonical Text

6. **Digest representation:** Use `sha256:<hex>`, RFC 6920 encoding, or an extensible
   algorithm/value object?
7. **Revision meaning:** Is `revision` solely resolver provenance, or can an immutable
   revision satisfy snapshot requirements without `text_hash`?
8. **Normalization edge cases:** Confirm the proposed preservation of BOM, final
   newline, NEL, and Unicode line separators, and define which byte-decoding profiles
   adapters may claim.
9. **Raw bytes:** Does a later profile need a raw-byte digest in addition to normalized
   `text_hash` for archival provenance?
10. **Authentication:** Document clearly that a digest detects mismatch but does not
    establish who authored or supplied the reference.

### Span Construction and Resolution

11. **Zero-length positions:** Should the protocol support cursor/insertion anchors, or
    retain non-empty quote-only spans? Supporting both likely requires a distinct
    PositionRef.
12. **Context policy:** Is context length a normative construction rule or caller
    policy? A shared default is convenient, but hard-coding 24 characters into the wire
    contract is unnecessary.
13. **Context semantics:** Should stale context be advisory when `exact` is unique, as
    FlexDoc behaves today, or a strict constraint whenever supplied?
14. **Snapshot-bound positions:** Confirm that a matching hash makes a verified offset
    authoritative among duplicate quotes.
15. **Grapheme boundaries:** Should validation reject spans that split a grapheme
    cluster, merely warn, or follow W3C's non-mandatory guidance?
16. **Approximate matching:** Which normalized or fuzzy strategies, if any, deserve
    standardized names and conformance vectors?
17. **Immutability:** Should resolution return an updated immutable SpanRef rather than
    mutate positions in place?
18. **Discontinuous selections:** Are multiple spans one TextRef collection, an
    annotation concern, or a future selector type?

### Safety, Privacy, and Evolution

19. **Quote limits:** What maximum `exact`, prefix, suffix, document size, and candidate
    count prevent denial of service and accidental copying of large copyrighted or
    sensitive passages?
20. **Extension behavior:** Reject unknown fields for typo safety, ignore them for
    forward compatibility, or require all extensions under a namespaced container?
21. **Versioning:** What changes are compatible within `textref/0.x`, and when does a
    new major become necessary?
22. **Governance:** Who owns releases and adjudicates behavior changes when tbd and
    FlexDoc need different policies?
23. **Package compatibility:** Does FlexDoc preserve the current import/module identity
    or take an intentional pre-1.0 breaking change when adopting the shared package?

These questions should be resolved in the protocol specification or explicit adoption
profiles. They should not be left to diverging implementation defaults.

## Recommendations

1. Create a standalone `textrefs` protocol repository.
2. Define one language-neutral specification, not separate Python and TypeScript specs.
3. Model TextRef as a compact profile of W3C `source + state + selector`.
4. Keep DocRef as a compact application locator, SnapshotRef as normalized-text
   identity, and SpanRef as a selector over supplied text.
5. Use a structured JSON TextRef as the normative data model, with a restricted YAML
   projection; defer a one-string projection.
6. Restrict v0.1 to normalized Unicode source text.
7. Keep all I/O and rendering in consumer-owned adapters.
8. Make typed ambiguity and snapshot status visible.
9. Use one shared conformance corpus for Python and TypeScript.
10. Resolve the normalization, fragment, snapshot-authority, zero-length, privacy, and
    extension questions before publishing v0.1.

## Next Steps

- [ ] Review and decide the open questions in this brief
- [ ] Create the standalone repository and protocol governance
- [ ] Write the four normative specifications and JSON Schemas
- [ ] Build shared golden fixtures before extracting implementation code
- [ ] Extract and harden the TypeScript DocRef implementation
- [ ] Extract the pure Python SpanRef implementation and write the TypeScript mirror
- [ ] Implement SnapshotRef and TextRef in both languages
- [ ] Integrate tbd at every DocRef-bearing boundary
- [ ] Integrate FlexDoc before its annotation and suggested-edit schema work
- [ ] Add rendered-text and fuzzy-resolution adapters only after source-text v0.1 is
  stable

## Methodology

This research reviewed:

- tbd v0.3.0 managed DocRef and docmap documentation
- The installed tbd TypeScript bundles for parsing, caching, fork manifests, and public
  exports
- FlexDoc's SpanRef, DocGraph source metadata, tests, design specification, and active
  roadmap
- Existing project research on stable span references, document models, and multilayer
  parsing
- Primary W3C, WICG, IETF, IANA, ECMAScript, Package URL, and Software Heritage sources

No implementation spike or performance benchmark was performed. Algorithm and package
recommendations are design conclusions; context-size, fuzzy-matching, and large-document
limits still require empirical validation.

## References

- [tbd DocRef format](https://github.com/jlevy/tbd/blob/main/packages/tbd/docs/references/docref-format.md)
- [tbd docmap format](https://github.com/jlevy/tbd/blob/main/packages/tbd/docs/references/docmap-format.md)
- [FlexDoc stable span-reference research](research-2026-05-30-span-references.md)
- [FlexDoc source-grounded document-model research](research-2026-05-29-document-model.md)
- [FlexDoc multilayer parsing research](research-2026-05-30-multilayer-parsing.md)
- [FlexDoc design specification](../../flexdoc-spec.md)
- [FlexDoc stabilization roadmap](../specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md)
- [W3C Web Annotation Data Model](https://www.w3.org/TR/annotation-model/)
- [W3C Character Model: String Matching](https://www.w3.org/TR/charmod-norm/#sec-Matching)
- [URL Fragment Text Directives](https://wicg.github.io/scroll-to-text-fragment/)
- [RFC 3986: URI Generic Syntax](https://www.rfc-editor.org/rfc/rfc3986.html)
- [RFC 5147: `text/plain` Fragment Identifiers](https://www.rfc-editor.org/rfc/rfc5147.html)
- [RFC 6920: Naming Things with Hashes](https://www.rfc-editor.org/rfc/rfc6920.html)
- [RFC 7493: I-JSON](https://www.rfc-editor.org/rfc/rfc7493.html)
- [RFC 7595: URI Scheme Guidelines](https://www.rfc-editor.org/rfc/rfc7595.html)
- [IANA URI Scheme Registry](https://www.iana.org/assignments/uri-schemes/uri-schemes.xhtml)
- [RFC 7763: The `text/markdown` Media Type](https://www.rfc-editor.org/rfc/rfc7763.html)
- [RFC 8259: JSON](https://www.rfc-editor.org/rfc/rfc8259.html)
- [RFC 8820: URI Design and Ownership](https://www.rfc-editor.org/rfc/rfc8820.html)
- [RFC 9530: Digest Fields](https://www.rfc-editor.org/rfc/rfc9530.html)
- [ECMAScript String Type](https://tc39.es/ecma262/#sec-ecmascript-language-types-string-type)
- [Package URL specification](https://github.com/package-url/purl-spec)
- [Software Heritage persistent identifiers](https://docs.softwareheritage.org/devel/swh-model/persistent-identifiers.html)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
