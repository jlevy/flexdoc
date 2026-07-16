# Research: A Portable DocRef, SpanRef, and TextRef Microformat

**Date:** 2026-07-10 (last updated 2026-07-16)

**Author:** Codex, synthesizing existing FlexDoc and tbd design work

**Status:** Research complete; FlexDoc direction and core protocol implemented

## Overview

tbd and FlexDoc each solve one part of the same reference problem:

- tbd’s **DocRef** locates a document and records where it came from
- FlexDoc’s **SpanRef** identifies a passage within source text and can recover that
  passage after offsets move

Neither type alone is a portable reference to a passage.
A DocRef does not select text, while a SpanRef assumes the caller already has the
correct source. A portable passage reference therefore needs two components:

1. A document locator
2. A selector within the resolved source

An optional source hash can additionally verify the canonical text against which a
position hint is computed.
It improves unchanged-document resolution, duplicate disambiguation, and stale-edit
detection, but it is not required for quote-based recovery after edits.

Motivating consumer scenarios include Google-Docs-style comments on Markdown,
Kindle/Readwise-style highlights and notes, bookmarks, and zero-width comments between
characters or at source boundaries.
Source-grounded suggested edits are a related consumer scenario, while Git patches and
redlines remain change representations above the reference layer.
Annotations live outside the document, retain enough of the selected text to remain
understandable when detached, and must survive edits through exact or approximate
re-anchoring. The shared protocol is **TextRef**, a compact composition of a DocRef, an
optional source validator, and a selector, with a language-neutral contract for Python
and TypeScript implementations:

```text
TextRef
├── document     DocRef locator and provenance
├── source_hash  optional validator for canonical source text
└── selector     optional typed selector; v0.1 defines span, point, and section
```

The four semantic target kinds are `whole_document`, `span`, `point`, and `section`.
The wire format represents `whole_document` by omitting `selector`, because selecting
the complete source needs no subresource evidence. APIs should still expose the four
kinds as an exhaustive enum rather than make callers infer them repeatedly.

One logical TextRef needs several projections because no single encoding is optimal for
storage, links, hand editing, and agent context:

- JSON is the normative value model and machine interchange form
- A restricted YAML sidecar hoists repeated document context for concise annotation sets
- A canonical TextRef URI is a one-reference clipboard, command-line, and deep-link form
- A contextual review view prints resolved source excerpts and annotations for people
  and agents without becoming persisted state

The recommended path is to prove one language-neutral specification and conformance
suite through FlexDoc and a concrete sidecar consumer, then extract a standalone package
when a TypeScript consumer needs the same persisted references.
The core should be pure and dependency-free.
Filesystem, network, Git, rendering, and application policy should remain in
consumer-owned adapters.

FlexDoc adopts this direction in the
[native TextRef integration plan](../specs/active/plan-2026-07-14-native-textref-integration.md).
That plan settles the FlexDoc binding API, consumer ownership of annotations,
contextual rendering boundary, and the unified `DocGraph/v0.2` contract. The remaining
open decisions below concern protocol limits, conformance details, later adapters, and
governance.

## Scope

Included:

- Unicode source documents, initially Markdown and other decoded text
- Local, application-internal, URL, GitHub, and GitLab document locators
- Optional validators for canonical source text
- Durable span, zero-width point, and Markdown-section selectors with contextual,
  positional, and structural evidence
- A normative JSON data model with an optional restricted YAML projection
- A canonical, round-trippable URI projection and an HTTPS viewer-link wrapper
- A language-neutral API contract, implemented in Python first and TypeScript when a
  second consumer requires it
- Deterministic validation, normalization, equality, and resolution behavior
- Adoption paths for tbd and FlexDoc

Excluded from the initial protocol:

- Annotation bodies, authorship, motivations, permissions, or workflow state
- Applying edits, generating diffs or redlines, and resolving edit conflicts
- Fetching, authentication, caching, redirects, or repository checkout
- Markdown rendering and source-to-rendered-text mapping
- Document Object Model (DOM), XPath, PDF geometry, optical character recognition (OCR),
  media, or binary selectors
- Conflict-free replicated data type (CRDT) anchors and live collaborative editing
- A normative fuzzy-matching algorithm or threshold
- A universal document graph or parser model
- Dedicated table, row, cell, heading, list-item, code-block, or other Markdown-node
  selector kinds
- A normative terminal or agent-prompt rendering

These exclusions keep the protocol useful without turning it into a document platform.
Excluding annotation bodies does not exclude the sidecar-annotation use case: the
protocol supplies target references, while a small consumer-owned envelope supplies
bodies, motivations, styles, tags, timestamps, and import provenance.
Excluding edit application has the same boundary: typed edit bodies, change sets, source
diffs, and redline projections can use TextRef targets without becoming part of TextRef.

## Terminology

- **DocRef:** A compact application reference that says where a document can be found.
  It is a requested locator and provenance record, not necessarily immutable identity.
- **SpanRef:** A selector for one non-empty range in already-available normalized source
  text. Its boundaries are Unicode code-point offsets and need not align with Markdown
  parser nodes.
- **Point selector:** The `type: point` branch of TextRef’s selector union, identifying
  one zero-width boundary between Unicode code points.
- **Section selector:** The `type: section` branch, identifying a complete CommonMark
  heading section from a durable start-heading anchor and optional end-heading anchor.
- **TextRef:** A DocRef with an optional source hash and optional typed selector.
  Its target kind is whole document, span, point, or section. Without a selector it
  refers to the whole document.
- **Source hash:** An algorithm-qualified strong validator for the canonical source
  text. It binds persisted position hints to one coordinate space but does not locate or
  retrieve historical content.
- **Resolver:** Consumer-provided code that obtains text and provenance for a DocRef.
- **Canonical source text:** The precisely normalized Unicode string against which
  source hashes and selector positions are computed.
- **Redline:** A review projection that displays old and new content together as
  deletions and insertions.
- **Change set:** One or more edit operations with shared base, ordering, validation,
  and application semantics.
- **Transport projection:** A reversible encoding of a TextRef for a URI, clipboard,
  command line, or another constrained channel.
- **Context view:** A derived, non-round-trippable rendering that combines resolved
  source excerpts, display line numbers, and annotation bodies for review.

Here, a *reference* may need contextual resolution and can fail; it is not necessarily a
globally unique or permanently dereferenceable identifier.

## Findings

### DocRef Is a Locator and Provenance Primitive

tbd DocRef v0.1 is a strict, single-string application grammar with these forms:

| Kind | Example | Resolution Context |
| --- | --- | --- |
| Internal | `internal:guidelines/python-rules.md` | Consuming application’s bundled documents |
| Local | `./docs/design.md` | Explicit caller-supplied filesystem base |
| Absolute local | `/srv/docs/design.md` | Host filesystem |
| URL | `https://example.com/design.md` | URL resolver |
| Git | `github:owner/repo@main//docs/design.md` | Git host and repository |

The grammar rejects bare relative paths, home-relative paths, and unknown schemes.
GitHub and GitLab file URLs normalize to provider-prefixed Git forms.
The `//` separator between Git revision and path permits revisions containing slashes.

The DocRef v0.1 document specifies syntactic equality after normalization, with one
additional local-path rule that ignores a single leading `./`. It does not claim that
two paths, URLs, branches, or provider spellings resolve to the same bytes.
This distinction is necessary: a branch DocRef can remain the same while its content
changes.

tbd currently uses DocRefs for:

- `docs_cache.files` source locations
- managed-document fork provenance
- generated docmap source fields
- `tbd docs add` inputs

tbd’s managed-document identity remains `kind + name`; DocRef records location and
provenance.
Its issue `spec_path` also remains a deliberately simpler repo-relative path.
Neither should be redefined as TextRef merely because TextRef exists.

The installed tbd v0.3.0 bundles expose several gaps that extraction needs to address:

- The source map contains parsing, formatting, normalization, and equality logic, but
  the installed package exposes no supported public DocRef API. Its internal bundled
  chunk does not export the formatter or equality helper, and normalization alone does
  not implement the documented leading-`./` equality rule.
- `tbd docs add` requires an explicit Git revision even though the base grammar permits
  no revision. This consumer-level restriction improves reproducibility but a branch
  revision remains mutable.
- DocRef validation is not applied uniformly at every configuration boundary.
- Git resolution can discover a commit, but tbd v0.3.0 does not persist that result as a
  general source validator or immutable DocRef.
- Fork manifests store an LF-normalized SHA-256 base hash.
  Their schema permits a source revision, but the current fork path does not populate
  it.
- Git fragments are parsed and preserved, URL fragments remain embedded in the URL, and
  `#` remains path text for local and internal references.
  None is resolved to document content.
- Internal and relative-local forms are contextual, not globally portable.

DocRef is therefore suitable for extraction, but extraction is partly specification work
rather than a mechanical package move.

### SpanRef Is a Durable Selector Over Supplied Text

FlexDoc’s current SpanRef has this shape:

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

- The `from_span()` and `from_node()` factories currently capture 24 code points of
  context on each side.
- `from_node()` depends on a FlexDoc Node and belongs in a FlexDoc adapter.
- Empty quotes and malformed coordinate pairs can be constructed but do not resolve
  meaningfully.
- Partial context scoring is useful recovery policy but needs explicit cross-language
  semantics if it is standardized.
- Mutation through `resolve_and_update()` may be less suitable than immutable value
  objects in a small protocol package.

### Span Boundaries Are Independent of Markdown Structure

A span selects an exact non-empty source slice. Its start and end may fall anywhere on
Unicode code-point boundaries: inside inline markup, across Markdown nodes, across
block boundaries, or around complete structural elements. Markdown parsing is not a
precondition for constructing or resolving it.

This source-level rule is important for comments on punctuation, formatting markers,
partial words, malformed Markdown, and ranges that a parser does not expose as one
node. Requiring node alignment would make parser choice part of basic reference
identity and prevent otherwise valid references from resolving in a text-only tool.

Semantic alignment remains useful as construction and operation policy:

- The v0.1 `SpanRef.from_span()` contract accepts any non-empty code-point range
- `SpanRef.from_node()` uses a parser-provided full source span
- A rendered-selection adapter maps visible text back to source before constructing a
  SpanRef
- An edit applicator may require token, node, or grapheme-cluster alignment even though
  the reference format does not

A span that crosses Markdown boundaries can be a valid source target while having no
single meaningful rendered-text projection. Exporters must refuse or split such a
projection rather than reinterpret the source range. Grapheme-cluster alignment is a
separate Unicode usability rule under consideration; it does not imply Markdown-node
alignment.

### Sections Need Boundary Anchors, Not Frozen Section Text

A section target represents the heading and all content it owns, including nested
subsections, through the start of the next heading of equal or higher level. Content
before the first heading is a preamble rather than a section. These rules match
FlexDoc's existing section model and CommonMark's parsed ATX and setext headings
([CommonMark](https://spec.commonmark.org/0.31.2/)).

Persisting the complete section as one `exact` quote would make any edit inside the
section invalidate its identity. A section selector should instead retain a SpanRef
anchor over the full source span of its starting heading. It may also retain a second
SpanRef anchor over the following equal-or-higher heading as independent evidence for
the exclusive end boundary. A Markdown structure adapter derives the current range
after the start anchor resolves.

This resembles the W3C RangeSelector's inclusive start selector and exclusive end
selector, but TextRef gives the section a semantic heading rule and permits the end
anchor to be omitted when a structure adapter can derive it
([Web Annotation](https://www.w3.org/TR/annotation-model/#rangeselector)). The end anchor
is corroborating and disambiguating evidence, not a frozen offset. Edits to section
content do not affect either heading anchor. Heading edits can use the same future
normalized or fuzzy relaxation policies as spans.

A section selector requires a declared Markdown structure profile and a compatible
adapter. A text-only resolver can still parse and transport it but reports
`unsupported` rather than guessing section boundaries. This keeps parser dependencies
out of the core while making semantic targeting explicit.
The v0.1 `commonmark` profile also applies to compatible supersets such as GFM when they
preserve CommonMark heading recognition. A dialect that changes which source blocks are
headings needs another named profile rather than silent parser-dependent behavior.

### Tables Use Spans Until Structural Identity Is Required

Version 0.1 can represent the common table cases without table-specific selectors:

- A phrase in a cell uses an arbitrary source span
- A whole cell or header cell uses its parser-derived source span
- A row or complete table uses the corresponding full source span when available
- A point between cell text and adjacent syntax uses a point selector

The word "header" should not become one ambiguous selector kind. A Markdown heading by
itself is a span, the content it owns is a section, and a table header cell is a span
over that cell's source. Future structural types should use distinct names such as
`heading` and `table_cell`.

A parser adapter must map a rendered cell selection to canonical source. Splitting a
row on raw `|` characters is incorrect because GFM permits optional outer pipes, trims
cell whitespace, parses inline markup, and allows escaped pipes inside cells
([GFM tables](https://github.github.com/gfm/#tables-extension-)).

This baseline does not preserve cell identity after the cell's entire text changes or
after rows and columns move. If a concrete consumer needs that behavior, future
`table`, `table_row`, or `table_cell` selector kinds can combine a table anchor,
row/column or header evidence, cell quote, and optional structural hints. Adding those
kinds does not change the span, point, section, or whole-document shapes. A dedicated
kind should wait for fixtures that establish how merged cells, missing headers,
alignment rows, row insertion, and dialect differences behave.

### A Source Hash Binds Position Evidence to Canonical Text

DocRef and SpanRef compose without a separate state object:

```text
DocRef ──resolve──> canonical source ──select──> SpanRef result
                              └─────── source_hash validator
```

A context-free offset cannot safely choose between duplicate quotes when the caller
supplies an unverified document.
If the TextRef’s `source_hash` matches the supplied canonical text, however, the offset
belongs to that exact coordinate space and can identify the intended duplicate.

The rule is:

- When `source_hash` matches, a valid position whose slice equals `exact` is
  authoritative for that source.
- When `source_hash` is absent or differs, the position is only a hint and quote/context
  re-anchoring remains conservative.

A source-bound TextRef should therefore normally retain its position hint.
The quote remains necessary for recovery after the document changes.
The hash is a strong validator, analogous to an HTTP strong validator, rather than a
retrievable archival version.
If reproducible retrieval is required, the DocRef must identify an immutable revision or
the consumer must retain a version locator or cached copy separately.

### Source Text and Rendered Text Are Different Representations

FlexDoc SpanRefs select normalized source Markdown.
Browser URL Text Fragments select rendered page text.
A Markdown source quote such as `**important**` does not identify the same character
stream as the visible word `important`.

TextRef v0.1 should define only canonical source text.
Browser fragments, rendered Markdown selectors, DOM ranges, and extracted PDF text
should use explicit adapters or future representation profiles.
A resolver must never silently reinterpret a source-text SpanRef against rendered text.

### Sidecar Annotations Exercise the Full Composition

Google-Docs-style comments on a Markdown document, stored out-of-band, use every part of
the proposed shape: a locator for the commented document, an optional source hash for
cheap staleness detection, and a durable selector per comment.
A sidecar file can hoist the shared parts to the top level and use bare `span`, `point`,
or `section` selectors per annotation, mirroring the FlexDoc guidance that an enclosing
container may supply document and source context:

```yaml
# design.md.comments.yaml -- a consumer schema over the protocol, not part of it
format: example-comments/0.1
document: ./design.md
source_hash: "sha256:83f6d4..."
comments:
  - id: c1
    author: alice
    created: 2026-07-12T09:14:00Z
    status: open
    selector:
      type: span
      exact: "Canonical source is authoritative."
      prefix: "The parser guarantees that "
      suffix: " Derived views are secondary."
      start: 1842
    body: Is this still true after the renderer refactor?
    replies:
      - author: bob
        body: Yes; see the selector parsing section.
```

The comment bodies, authors, threads, and resolution state are the consumer’s schema.
The protocol contributes the anchoring contract, which gives the sidecar a precise
lifecycle:

1. On save, capture each comment’s quote or boundary context and position, then record
   the file-level source hash.
2. On load, hash the current document text.
   If it matches `source_hash`, positions can use direct verified lookup.
3. If the hash differs, re-anchor every selector through the exact resolution tiers.
4. Move the sidecar to the new coordinate space atomically: refresh every resolved
   position, remove stale positions from unresolved selectors, then update the shared
   `source_hash`. A consumer that needs the old position for diagnostics may retain it
   in annotation history or as a `last_known_target`, outside the active selector.
5. A selector that fails to re-anchor becomes visibly orphaned, retaining its quote or
   boundary context for later recovery or human reconciliation.
   It must not be silently dropped or guessed into place.
6. An approximate match is a candidate, not a new fact.
   Persist updated selector evidence only after explicit user confirmation or another
   consumer-defined high-assurance check.

The orphaned state is not hypothetical polish.
User studies of annotation systems show that when anchor text is deleted, users prefer
an honest orphan over a confident wrong guess (Brush et al., CHI 2001). A 2015 study of
20,953 Hypothesis annotations reports about 22% already orphaned on the live web and 53%
of the remainder at risk if the page changes.
Even quote anchoring with multiple selectors loses a meaningful fraction of anchors over
time, so the format must represent failure explicitly rather than promise lossless
survival.

### Highlights, Notes, and Edit Proposals Need an Envelope, Not a Larger TextRef

A reference answers *where*; an annotation answers *what a user did or proposes there*.
Kindle, Readwise, and the 2026 EPUB Annotations draft all reinforce this separation.
A useful highlight record may contain selected text, a note, color, tags, timestamps,
provider IDs, and a book location, but none of those fields changes the identity of its
target.

The smallest useful consumer profile is an envelope around TextRef:

```yaml
format: text-annotation/0.1
id: a-42
target:
  format: textref/0.1
  document: ./book-notes.md
  source_hash: "sha256:83f6d4..."
  selector:
    type: span
    exact: "Robust anchors use independent evidence."
    prefix: "The central rule is: "
    suffix: " Offsets alone are insufficient."
    start: 913
motivations: [highlighting, commenting]
body:
  type: text
  value: Relate this to the re-anchoring policy.
style:
  color: yellow
  emphasis: solid
tags: [anchoring]
created: 2026-07-12T09:14:00Z
provenance:
  system: readwise
  external_id: "987654"
  location:
    type: page
    start: 57
    end: 58
```

This is a proposed consumer profile, not part of `textref/0.1`. Its deliberately small
rules are:

- `target` is the only required relationship to the reference protocol.
- `motivations` is an array because one annotation can both highlight and comment.
  The core use-case vocabulary is `highlighting`, `commenting`, and `bookmarking`.
  Review tools can also use the Web Annotation motivations `editing` and `classifying`;
  namespaced tokens can add consumer-specific motivations.
- `body` is optional. Version 0.1 needs only a discriminated plain-text body; later
  profiles can add typed rich-text, media, or edit bodies without changing TextRef.
- `style` is optional annotation presentation.
  `color` is a semantic token rather than an RGB value, so a reader can map it to the
  current theme. Common EPUB vocabulary values are `pink`, `orange`, `yellow`, `green`,
  `blue`, and `purple`; unrecognized string tokens should be preserved, while exact
  vendor styling belongs in namespaced extensions.
  `emphasis` has the common `solid`, `underline`, `strikethrough`, and `outline` values
  and follows the same preservation rule.
- Tags, authorship, permissions, threads, workflow state, and timestamps are envelope
  concerns. They should not make otherwise identical TextRefs unequal.
- Workflow status such as `unresolved`, `needs_clarification`, or `fixed` is independent
  of target resolution.
  An annotation may remain unresolved while its selector is anchored, relocated,
  ambiguous, or orphaned.
- Annotation IDs identify annotation records, not targets.
  A container must permit several annotation IDs to share the same TextRef instead of
  keying records by target.
- App-specific structured data belongs under a namespaced `extensions` object rather
  than as unregistered top-level fields.
- Provider locations such as page, Kindle location, Readwise order, offset, or time
  offset are import provenance and useful display hints.
  They are not Unicode source positions and must never be copied into `selector.start`
  without a representation adapter.

`selector.exact` already preserves the selected source text, so a Markdown highlight
does not also need `highlight_text`. An optional envelope field such as `captured_text`
is justified only when the exported user-visible text differs from the canonical source
quote, as when a rendered heading omits Markdown markers, or while an imported
Kindle/Readwise highlight has not yet been mapped to accessible source text.
An unresolved import record may retain `captured_text`, provider location, ASIN, ISBN,
title, and author, but it does not become a valid TextRef until an adapter identifies a
document representation and target in that representation.

The basic annotation cases compose with the four v0.1 target kinds:

| User Action | Target | Envelope |
| --- | --- | --- |
| Highlight text | `span` selector | `highlighting`; optional style |
| Highlight with note | `span` selector | `highlighting` and `commenting`; text body |
| Comment on text without visible highlight | `span` selector | `commenting`; text body |
| Bookmark or cursor marker | `point` selector | `bookmarking`; optional label/body |
| Note between characters or at a line boundary | `point` selector | `commenting`; text body |
| Document-level note | No selector | `commenting`; text body |
| Proposed insertion | `point` selector | `editing`; typed edit body with source content |
| Proposed deletion | `span` selector | `editing`; typed delete body |
| Proposed replacement | `span` selector | `editing`; typed edit body with source content |
| Comment on a whole Markdown block | `span` selector over its full source span | `commenting`; text body |
| Comment on table or cell content | `span` selector over the mapped source range | `commenting`; optional captured rendered text |
| Comment on a complete heading section | `section` selector | `commenting`; text body |
| Answer an embedded question | `span` selector over the question block | `replying`; typed answer body in a later profile |

Publication identity remains a separate portability problem.
EPUB annotation sets use publication metadata and prefer ISBN when available; Readwise
records Kindle ASINs, book IDs, and provider locations.
That information can help an importer choose an edition, but it does not prove that two
editions have the same character stream.
The source hash and selector evidence must bind to the actual representation used for
resolution.

### Point Targets Are Boundaries, Not Empty Quotes

A cursor, insertion mark, bookmark, or note between characters selects no text.
Encoding it as `exact: ""` or as an accidental one-character range makes quote matching
ambiguous and cannot express which adjacent content owns the location.
The DOM’s collapsed ranges and EPUB CFI’s character offsets provide the better model: a
point is a boundary between code points, plus explicit side affinity.

TextRef v0.1 should therefore define a distinct `point` selector:

```json
{
  "type": "point",
  "position": 1842,
  "affinity": "before",
  "prefix": "the text immediately before",
  "suffix": "the text immediately after"
}
```

`position` is the zero-based code-point boundary in `[0, code_point_length(text)]`.
`prefix` ends immediately before the boundary and `suffix` starts immediately after it.
Affinity defines insertion behavior and the owning side of the anchor:

- `before` attaches the point to preceding content.
  Text inserted at the boundary falls after the point; the prefix is the primary
  recovery context.
- `after` attaches the point to following content.
  Text inserted at the boundary falls before the point; the suffix is the primary
  recovery context.

This distinction matters at exactly the boundaries users care about:

| Intent | Source Target |
| --- | --- |
| Mark one visible character | A one-code-point `span` selector over that character |
| Insert before a character | A `point` before it, normally with `after` affinity |
| Insert after a character | A `point` after it, normally with `before` affinity |
| End of a non-final line | The boundary immediately before canonical `\n`; affinity depends on whether the anchor owns the preceding text or following newline |
| End of the final line | The document-end boundary, with `before` affinity |
| Start of a line | The boundary after the preceding `\n`, with `after` affinity |
| Annotate a Markdown heading only | A `span` selector over the heading node’s full source span |
| Annotate a heading and all content it owns | A `section` selector anchored at that heading |
| Insert before or after a heading | A `point` at the heading source span’s start or end |

At a non-final line end, `before` keeps the point attached to the existing line text;
new text inserted at that boundary follows the point.
`after` keeps it attached to the newline, so text inserted before the newline precedes
the point and the marker remains at the logical line end.
At the end of the document there is no following context, so a portable content anchor
can attach only to preceding text; preserving a semantic “always at document end” marker
through future appends requires editor history or an application-level rule.

For a heading or other parsed object, annotating the object itself should normally use
the range of Markdown source represented by `Node.source_span`, including source syntax
that belongs to that span.
An insertion point immediately before the heading normally uses `after` affinity to
follow the heading if content is inserted ahead of it; a point immediately after the
heading normally uses `before` affinity to remain attached to the heading.
Annotating a rendered label such as `Heading` while the source is `## Heading` requires
a rendering-to-source adapter; the resolver must not silently treat the two character
streams as identical.
The annotation envelope may retain the visible `captured_text` while TextRef retains the
canonical source quote.

### Cross-Language Semantics Require More Than Matching Data Classes

Python indexes strings by Unicode code points in normal cases.
JavaScript indexes strings by UTF-16 code units.
The same integer therefore selects different content after many non-BMP characters
unless TypeScript converts explicitly.

A shared protocol must also settle:

- Unpaired surrogate handling
- Newline normalization
- Digest input and encoding
- Half-open interval semantics
- Duplicate-quote behavior
- Context construction and comparison
- Safe integer limits in JSON
- Unknown-field behavior

JSON Schema can validate structure but cannot define these algorithms.
Normative prose and shared golden vectors are both required.

## Relevant Standards and Prior Art

### W3C Web Annotation Provides the Core Conceptual Model

The W3C Web Annotation Data Model represents a selected resource as:

- `source`: the resource
- `state`: the intended representation of that resource
- `selector`: a segment within that representation

The concepts map to TextRef, but not directly.
DocRef maps to `source`, and SpanRef maps to selector evidence.
W3C `state` describes how to retrieve the intended representation, such as a timestamp,
cached copy, or request headers; `source_hash` only verifies canonical text supplied by
a resolver. Its TextQuoteSelector supplies `exact`, `prefix`, and `suffix`; its
TextPositionSelector supplies zero-based half-open positions.
The Recommendation mandates offsets in Unicode code points ("The selection of the text
MUST be in terms of unicode code points … not in terms of code units"), requires logical
text order, and states normatively that selections SHOULD NOT split grapheme clusters.
The residual interoperability hazard is implementations ignoring this requirement, not
an omission in the standard.

The full Web Annotation JSON for Linking Data (JSON-LD) and Resource Description
Framework (RDF) model also covers bodies, motivations, agents, styles, multiple
resources, states, and protocol concerns.
Adopting all of it would make the common low-level reference harder to embed.
The W3C model also says that a TextQuoteSelector with multiple surviving matches should
select all of them.
TextRef’s conservative `resolve_one` instead reports ambiguity, while
`resolve_all` can preserve the W3C behavior.
TextRef should document these mappings and intentional differences rather than claim
round-trip equivalence or depend on the full JSON-LD model.

### EPUB CFI Demonstrates Extensible Recovery Evidence

EPUB Canonical Fragment Identifiers provide an established model for durable locations
in changing documents.
An EPUB CFI combines a structural path and character position with optional assertions
about identifiers and text immediately before or after the target.
Resolvers verify those assertions, correct stale paths when they can recover the target,
and treat unrecoverable references as invalid.

The design is instructive even though EPUB CFI is tied to EPUB’s XML structure and uses
UTF-16 code-unit offsets:

- Positional data remains useful when it is verified by independent evidence.
- Preceding and following text can both detect drift and relocate a target.
- Corrected references can replace stale position hints without changing the logical
  target.
- Extension parameters allow new recovery heuristics while old processors ignore what
  they do not understand.
- Side bias records whether a zero-width location belongs with preceding or following
  content, which is useful prior art for TextRef point selectors.

TextRef should reuse the recovery pattern, not EPUB CFI’s path grammar, fragment syntax,
or UTF-16 coordinate system.

### EPUB Annotations and Readwise Cover the Consumer Layer

The W3C EPUB Annotations 1.0 Working Draft, published 21 May 2026, is the most directly
relevant current design for portable book annotations.
It describes notes, highlights, and bookmarks as annotations with a target, optional
body, motivation, timestamps, creator, style, and tags.
Targets can carry multiple selectors so an exporter can include both precise and
modification-resistant evidence.
The companion use cases explicitly require highlights with optional notes, colors and
styles, bookmarks at cursor locations, and reattachment after words are inserted before
or within the target.

Its annotation-set `about` metadata also shows why publication matching should remain
outside TextRef. ISBN is preferred, but the draft acknowledges that EPUB has no
universally accepted identifier and importers often need title, creator, publisher, and
other heuristics. Those fields identify a likely publication or edition; selectors still
identify a target within a chosen representation.

The draft is useful prior art, not a stable dependency.
It is explicitly work in progress, some selector integration remains at risk, and parts
of its extension model are still under development.
TextRef should retain its smaller JSON profile while offering a directional mapping to
EPUB/Web Annotation concepts.

Readwise’s official API supplies concrete import evidence from production systems.
Highlights contain text, optional notes, color, tags, timestamps, external IDs, start
and end locations, and a `location_type` such as page, location, order, offset, or time
offset. Book records may identify Kindle as the source and retain an ASIN. These are
valuable annotation and provenance fields, but most are not source-text coordinates.
Readwise Reader also documents that a highlight may remain visible in its notebook when
the service cannot confidently match it back to article text, validating explicit orphan
and candidate states.

Amazon’s public help establishes cross-device synchronization for Kindle notes and
highlights, but does not publish a stable, general annotation interchange schema.
Kindle should therefore be treated as an important use case and import adapter, not as
the source of protocol semantics.

### Validators and Historical Versions Are Different Concepts

HTTP distinguishes validators from stored historical representations.
A strong ETag or collision-resistant representation hash can test whether content is the
same and guard authoring operations against lost updates.
It does not provide a way to retrieve an old representation.
Memento, Git commits, archived copies, and immutable content locators address that
different problem.

TextRef should therefore call the optional field `source_hash` and define it as a strong
validator over canonical source text.
An immutable Git revision belongs in the DocRef.
Other version locators, cached copies, capture timestamps, and audit history belong in a
consumer’s provenance model until a concrete cross-consumer need justifies a typed state
object.

### Generic URI Fragments Are the Wrong Extension Point

RFC 3986 defines a fragment as a client-resolved secondary-resource identifier whose
semantics depend on the retrieved media type.
RFC 8820 consequently warns applications not to impose a generic fragment grammar across
media types they do not control.

This argues against forms such as:

```text
github:owner/repo@main//docs/design.md#span=<encoded-selector>
```

Such a string conflates document retrieval and passage selection, requires difficult
escaping, and creates inconsistent behavior across Markdown source, rendered HTML, local
files, and provider URLs.

tbd may continue accepting fragments in standalone DocRefs for compatibility and
presentation.
TextRef should prevent a recognized Git or URL fragment from competing with
`span`, so one object never contains two authoritative passage selectors.
Before this becomes a schema rule, DocRef must define fragment extraction for each kind.
In particular, `#` can be valid path text in local and internal references.

### Browser Text Fragments Are an Export Format

The `#:~:text=` URL format (“text fragments,” originally “scroll-to-text fragment”) uses
the same quote-plus-context shape as SpanRef, so it deserves a close look: it is the one
selector format ordinary users encounter, every major browser now implements it, and a
TextRef exporter should be able to emit it.
Its navigation-specific behavior makes it unsuitable as the persisted protocol format.
The related [span-references research](research-2026-05-30-span-references.md) provides
a compact summary and an incompatibilities-to-bridge list.

#### Standardization Status

The normative home is the WICG
[URL Fragment Text Directives](https://wicg.github.io/scroll-to-text-fragment/) Draft
Community Group Report (December 2023, edited by Google engineers), written as
monkeypatches to the HTML, DOM, and Fetch standards.
It is not on the W3C standards track, and the WHATWG URL Standard contains no
fragment-directive concept (the 2019 proposal, whatwg/url#445, closed without merging).
Upstreaming into the WHATWG HTML Standard began in November 2025
([whatwg/html#11895](https://github.com/whatwg/html/pull/11895), still a draft as of
July 2026, with a companion Fetch change for the user-activation bit).
“Draft” no longer implies low adoption: the format has shipped in every engine since
October 2024, and Mozilla’s standards position is positive.
The precise characterization is “standardized outside the WHATWG standards track and
currently being upstreamed into HTML,” with browser-navigation semantics.

#### Syntax and the Fragment Directive

The `:~:` delimiter separates an ordinary URL fragment from the **fragment directive**,
a deliberately extensible `&`-separated directive list in which unknown directives are
ignored. `text=` is the only directive shipped anywhere.
Its grammar:

```text
#:~:text=[prefix-,]textStart[,textEnd][,-suffix]
```

- `textStart` alone requests the first exact match of that string.
- `textStart,textEnd` is a range match: from the first instance of `textStart` to the
  next instance of `textEnd` after it, keeping URLs short for long passages.
  SpanRef has no analog of this form; an exporter must choose between a long exact term
  and a lossy range.
- `prefix-` and `-suffix` are context terms for disambiguation.
  They must surround the match but tolerate any whitespace between context and match, so
  context can sit in adjacent elements.
  They are not highlighted.
- Multiple independent `text=` directives may be joined with `&`; all matches are
  highlighted and the first is scrolled into view.
- Inside every term, `-`, `&`, and `,` must be percent-encoded (`%2D`, `%26`, `%2C`)
  because they are structural.
  The parser is strict: a literal dash anywhere in a decoded term, or an empty term,
  invalidates the whole directive.
  Terms are percent-decoded as UTF-8, and multilingual text appears in logical order.

Browsers strip the fragment directive from every script-visible URL surface derived from
session history: `location.hash` and `document.URL` never contain it, and `hashchange`
does not fire when only the directive changes.
The stripping does not apply to plain string APIs such as `new URL(...)`, so tools that
parse raw URLs still see `:~:`. A DocRef parser that accepts URLs should therefore
expect and preserve (or explicitly reject) fragment directives rather than treating them
as opaque fragment text.

#### Matching Semantics Differ From Exact Source Matching

Every step of text-fragment matching diverges from this protocol’s exact,
source-grounded resolution:

- **Rendered text only.** Matching walks visible rendered text: `display: none` and
  `visibility: hidden` content, scripts, styles, images, and media never match, and
  whitespace is collapsed as rendered.
  Markdown source syntax such as `**important**` is unreachable; only the rendered word
  is.
- **Case- and accent-insensitive.** The spec requires a base-character comparison at the
  primary collation level of UTS #10: case, accents, and other marks are ignored.
- **Word-bounded.** Matches must start and end on UAX #29 word boundaries, locale-aware
  and dictionary-based for languages written without spaces.
  This is a security mitigation (it prevents guessing a secret one character at a time),
  and it makes sub-word selections inexpressible.
  Word segmentation for CJK and other unsegmented scripts remains a known pain point.
- **Block-constrained.** Each individual term (`prefix`, `textStart`, `textEnd`,
  `suffix`) must lie within one block-level element, though a whole range match may span
  blocks.
- **First match wins, failure is silent.** Only the first match in document order is
  targeted. A failed or malformed directive falls back to ordinary fragment behavior with
  no error reported to the user or the page; by design nothing about the match is
  observable to scripts, and even the search timing must not reveal success.
  There is no ambiguity reporting at all, where this protocol treats ambiguity as a
  first-class visible outcome.

The activation and security model further narrows where the format works: text
directives are honored only on user-activated navigations (one activation per gesture),
only in top-level frames, only for `text/html` and `text/plain`, and cross-origin
navigations must be opener-isolated (hence the guidance to add `rel="noopener"`). Sites
can opt out entirely with the `Document-Policy: force-load-at-top` response header.
Highlights are styled by the UA and, since CSS Pseudo-Elements Level 4, by authors
through the `::target-text` highlight pseudo-element (limited to color, background,
decoration, and shadow properties).

#### Browser Support Is Broad but Recent

| Engine | Navigation support | `::target-text` | `document.fragmentDirective` |
| --- | --- | --- | --- |
| Chrome (and Chromium family) | 80 (Feb 2020; some compatibility tables list 81) | 89 | 86 |
| Edge | 83 (May 2020) | 89 | 86 |
| Safari (macOS and iOS) | [16.1](https://webkit.org/blog/13399/webkit-features-in-safari-16-1/) (Oct 2022) | 18.2 (Dec 2024) | 18.4 (Mar 2025) |
| Firefox (desktop and Android) | [131](https://developer.mozilla.org/en-US/docs/Mozilla/Firefox/Releases/131) (Oct 2024) | 131 | 131 |

Firefox 131 completes navigation support across the major browser engines.
Feature detection is `'fragmentDirective' in document`, with one notable trap:
[Safari 16.1 through 18.3 supports navigation without exposing the API](https://bugs.webkit.org/show_bug.cgi?id=273466),
which produces false negatives.
Text directives apply to full navigations rather than single-page application route
changes.

Current Chrome, Safari, and Firefox releases provide native link-creation commands:
[Chrome “Copy link to highlight”](https://support.google.com/chrome/answer/10256233),
[Safari 18.2 “Copy Link with Highlight”](https://webkit.org/blog/16301/webkit-features-in-safari-18-2/),
and
[Firefox 145 “Copy Link to Highlight”](https://www.firefox.com/en-US/firefox/145.0/releasenotes/).

#### Enhancements and Adjacent Proposals

- **A richer JavaScript API is proposed but unshipped.** The
  [fragment-directive-api explainer](https://github.com/WICG/scroll-to-text-fragment/blob/main/fragment-directive-api.md)
  adds `FragmentDirective.items`, a constructible `TextDirective`,
  `createSelectorDirective(Range | Selection)` (programmatic generation from a
  selection), and `SelectorDirective.getMatchingRange()`, which would finally provide
  error reporting and a bridge to the CSS Custom Highlight API. It has sat behind a
  Chrome flag since Chrome 97 and remains “Proposed.”
- **Non-text directives exist only as explainers.** A `selector()` directive
  ([EXTENSIONS.md](https://github.com/WICG/scroll-to-text-fragment/blob/main/EXTENSIONS.md))
  would target elements by CSS selector with a strict attribute allowlist, adapted from
  the W3C Annotation CSS selector; a `note()` directive has also been floated.
  Nothing beyond `text=` has shipped in any browser.
- **The generation algorithm is instructive prior art for an exporter.** Chromium’s
  `TextFragmentSelectorGenerator` snaps selection endpoints outward to word boundaries,
  uses an exact term for single-block selections up to 300 characters and a range
  otherwise, adds context immediately for selections under 20 characters, and then
  iteratively adds context or range words (at least 3, at most 10 per side) while
  re-testing against the page until the match is unique or generation fails.
  A SpanRef-to-fragment exporter faces the same uniqueness search and should expect to
  refuse when it cannot disambiguate.
- **Userland tooling provides maintained implementations.** GoogleChromeLabs’
  [text-fragments-polyfill](https://github.com/GoogleChromeLabs/text-fragments-polyfill)
  provides both matching and generation utilities, is actively maintained, and powers
  Chrome on iOS (which cannot reuse Blink’s native implementation over WKWebView).
- **The lineage is shared.** The text directive’s quote-plus-context design and the W3C
  TextQuoteSelector descend from the same annotation-selector work, which is why a clean
  mapping from SpanRef exists at all; the Hypothesis project has discussed emitting
  text-fragment URLs for its annotations for exactly this reason.

#### Implications for TextRef

The projection from a SpanRef is lossy and directional: `exact` maps to `textStart` (or
a `textStart,textEnd` range for long quotes), `prefix` and `suffix` map to context
terms, everything is percent-encoded (structurally `-`, `,`, `&`), and positions and
source validation drop out entirely.
An exporter must also refuse spans the format cannot express: case-significant quotes
(matching is case-insensitive), sub-word spans (word-boundary rule), terms crossing
block boundaries, and content that does not appear in rendered text.
FlexDoc already ships this projection as `SpanRef.to_text_fragment()`, which encodes the
structural delimiters correctly but projects source text directly with only a docstring
caveat about the rendered-text mismatch; its post-extraction home should be a
rendered-text adapter, not the protocol core.
The import direction, parsing `#:~:text=` into a rendered-text SpanRef, is mechanically
simple but inherits the rendered-text profile question and is out of scope for v0.1.

Text fragments are transient by design: the specification’s link-lifetime guidance
frames them for sharing rather than archival use.
They match loosely against a representation TextRef does not define, report nothing on
failure, and have no source validator or position concept.
TextRef should therefore treat text fragments as a well-specified, refusable export
projection rather than a persisted foundation.

### Portable TextRef Links Need a Dedicated Codec

A portable link must represent the TextRef object itself rather than append a private
selector to the target document’s fragment.
This preserves the media-type ownership rule: the document keeps its own fragment
semantics, while a TextRef-aware application owns the link codec.

Two deployment forms serve different environments:

1. A proposed `textref:` URI is compact, self-contained, and independent of a web
   service. It works as a clipboard, command-line, configuration, and registered
   application deep-link value.
2. An HTTPS viewer URL puts the same `textref:` value after the viewer’s `#`. It is
   clickable in applications that do not register custom schemes, and the fragment is
   not sent in the HTTP request.

For example, the readable form can use a versioned scheme-specific path and query
parameters:

```text
textref:0.1?doc=.%2Fdesign.md&type=span&exact=Canonical%20source&start=1842
```

A conforming viewer can wrap it without changing the inner value:

```text
https://viewer.example/open#textref:0.1?doc=.%2Fdesign.md&type=span&exact=Canonical%20source&start=1842
```

`textref` is not currently registered in the IANA URI Scheme Registry.
Public use therefore requires a stable scheme specification and at least provisional
registration under RFC 7595. Until that governance step, implementations can exercise
the codec as a plain string and use an application-controlled HTTPS viewer URL for
clickable links
([registry](https://www.iana.org/assignments/uri-schemes/uri-schemes.xhtml),
[registration guidance](https://www.rfc-editor.org/rfc/rfc7595.html)).

The URI should remain a reversible transport projection of the JSON object.
It should not introduce abbreviated selector semantics, silently omit context to meet a
length limit, or embed a compressed tuple as the only form.
Compression, encryption, and server-stored short links can wrap the URI when needed, as
Plannotator demonstrates, but each is a separate transport with separate privacy and
lifetime properties.

Long quotes still make long URLs.
A URI exporter needs a documented size limit and a visible refusal result.
Quotes and annotation bodies may be sensitive even when an HTTPS wrapper keeps its
fragment out of the request: browsers, chat systems, clipboard managers, screenshots,
and history can still retain the complete URL.

### Line References Are Useful Inputs and Displays, Not Durable Selectors

Line notation is widespread because it is cheap to produce and easy to discuss:

- RFC 5147 defines zero-based `char` and `line` positions and half-open ranges for
  `text/plain`, including zero-width positions and optional integrity checks.
  It warns that edits break the coordinates and that line-ending and character-encoding
  rules affect interpretation ([RFC 5147](https://www.rfc-editor.org/rfc/rfc5147.html)).
- The `text/markdown` media-type registration defines `#line=10` as the eleventh source
  line and permits Markdown variants to define additional fragment parameters
  ([RFC 7763](https://www.rfc-editor.org/rfc/rfc7763.html)).
- GitHub uses one-based `#L14` and `#L14-L20` anchors.
  Its durable workflow combines those line anchors with an immutable commit URL and
  requires `?plain=1` for Markdown source
  ([GitHub permalinks](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-a-permanent-link-to-a-code-snippet)).
- Reviewdog accepts the familiar `file:line:column: message` diagnostic form and richer
  ranged JSON, then filters diagnostics against a Git diff before posting review
  comments ([reviewdog](https://github.com/reviewdog/reviewdog)).

These precedents justify line-based construction and presentation, but not a durable
`line` selector.
A line number changes after any earlier inserted or deleted newline, and
a coarse whole-line target discards the selected words and boundary evidence.
RFC 5147’s integrity check and GitHub’s immutable commit make stale coordinates
detectable or stable; neither relocates them in a changed document.

A consumer should therefore accept shorthand such as `design.md:L42-L44`, resolve it
against a supplied source representation, and immediately construct an ordinary text
selector over those full source lines.
The resulting TextRef retains `exact`, context, the code-point `start`, and an optional
source hash. A line-boundary input similarly constructs a point selector.
After resolution, APIs and context renderers can derive one-based line and column labels
again.

Line-only links remain appropriate when the document locator is immutable or the user
explicitly wants an ephemeral pointer.
They should be advertised as a navigation or authoring shorthand, not as the robust
TextRef export.

### Content-Addressed Formats Solve Narrower Problems

- **Package URL (purl)**, standardized as ECMA-427 in December 2025, identifies
  packages, versions, qualifiers, and package-relative subpaths.
  A document is not generally a package, and passages are not package subpaths.
- **Software Heritage identifiers (SWHIDs)**, standardized as ISO/IEC 18670:2025,
  provide strong content-addressed source identities with origin, visit, anchor, path,
  and line qualifiers (a revision is a core identifier type, not a qualifier).
  They are valuable for archived software citations but do not cover
  application-internal, local, or general URL documents, and line selectors remain
  edit-fragile.
- **RFC 6920 `ni` identifiers** name content by algorithm-qualified digest but do not
  locate a mutable document or define TextRef’s normalized-text digest input.

These formats reinforce the distinction between location, content identity, and
selection. None replaces the proposed composition.

### Annotation Systems Support Quote-Primary Anchoring

Production annotation systems and the research literature behind them converge on the
same design the protocol proposes: redundant selectors with the quote as ground truth,
ordered re-anchoring, and explicit failure.

- **Hypothesis** stores three selectors per annotation (RangeSelector,
  TextPositionSelector, and TextQuoteSelector with 32 characters of prefix and suffix
  context) and re-anchors through an ordered cascade, verifying every positional hit
  against the stored quote
  ([fuzzy anchoring](https://web.hypothes.is/blog/fuzzy-anchoring/)). The original 2013
  implementation used Google diff-match-patch (Bitap matching, which caps patterns at 32
  characters); the current client re-anchors with
  [approx-string-match](https://github.com/robertknight/approx-string-match-js) (Myers
  1999 bit-parallel matching, no pattern-length cap), allowing
  `maxErrors = min(256, quote.length / 2)` and scoring candidates with weights of 50 for
  quote similarity, 20 each for prefix and suffix, and 2 for proximity to the stored
  position
  ([match-quote.ts](https://github.com/hypothesis/client/blob/main/src/annotator/anchoring/match-quote.ts)).
  Quote dominates; context disambiguates repeats; the stored offset is only a
  tie-breaker. Annotations that fail every strategy are shown as orphans rather than
  discarded.
- **Orphan rates are significant even with this machinery.** Aturban, Nelson, and Weigle
  ([Quantifying Orphaned Annotations in Hypothes.is](https://arxiv.org/abs/1512.06195),
  2015\) report that about 22% of a 20,953-annotation sample are already orphaned, 53%
  of the still-attached annotations are at risk if the page changes, and only about 12%
  of orphans are recoverable from web archives.
- **Apache Annotator** is a retired, archived implementation of W3C selector creation
  and resolution. Its matching remains exact-only; its fuzzy quote matching proposal has
  no implementation. The maintained lineage of working anchoring code is the Hypothesis
  client, not the standards project.
- **The research lineage is older than the web annotation tools.** Phelps and Wilensky’s
  robust intra-document locations (WWW9, 2000) store redundant independent descriptors
  (unique ID, structural tree walk, surrounding context) with ordered reattachment and
  graceful degradation.
  Brush et al. (CHI 2001) report that users judge re-anchoring by the unique words of the
  anchor text and prefer honest orphans over wrong guesses; the companion Microsoft tech
  report proposes keyword anchoring (rarest words plus inter-keyword distances), which
  tolerates rewording that defeats exact-quote matching and is a plausible future
  evidence type for approximate strategies.
- **diff-match-patch itself is now legacy.** The Google repository is archived; a
  maintained Python fork exists, but its Bitap matcher still caps patterns at the
  machine word. New implementations should prefer the Myers 1999 approach for long
  quotes.

The protocol’s resolution tiers, conservative ambiguity handling, and visible failure
axis match this consensus.
An optional `source_hash` adds cheap change detection: a resolver can distinguish
“unchanged, verify the position” from “changed, re-anchor” with one document hash rather
than repeated searches.
The current Hypothesis quote matcher returns the highest-scoring candidate within its
error budget; TextRef should add an absolute acceptance threshold and a minimum margin
over the runner-up before an approximate candidate is considered resolved.

### Context Diffs Show the Value and Risk of Progressive Relaxation

Unified diffs pair expected line numbers with surrounding context.
GNU `patch` first searches for all context, then progressively ignores outer context
lines according to its fuzz factor.
It reports offsets, fuzz use, and rejected hunks rather than assuming every hunk belongs
somewhere. The manual explicitly warns that larger fuzz factors increase the chance of
applying a hunk incorrectly.

TextRef should follow the same posture:

- Start with all available evidence and relax it in named stages.
- Keep the old position as a proximity hint, not proof.
- Report the method and evidence used for a successful relaxation.
- Reject or expose candidates when evidence is weak rather than always selecting the
  closest text.

Unlike a patch hunk, a SpanRef has character-level quote and context evidence and does
not carry an edit to apply.
The analogy concerns the conservative relaxation ladder and visible failure behavior,
not the diff wire format.

### Contextual Diagnostics Provide the Agent Export Pattern

Several mature formats separate structured locations from a readable context rendering:

- SARIF stores a precise `region`, an optional source `snippet`, and a larger
  `contextRegion` whose stated purposes are display context and improved result
  matching. The context is redundant derived evidence rather than the finding’s sole
  location ([SARIF](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)).
- Rust compiler JSON diagnostics carry byte and one-based line/column ranges, complete
  source lines with per-line highlight columns, labels, suggested replacements, and an
  optional `rendered` terminal diagnostic.
  Consumers can use structured fields or show the familiar annotated source form
  ([rustc JSON](https://doc.rust-lang.org/beta/rustc/json.html)).
- GitHub review comments bind a body to a commit, path, side, and single- or multi-line
  range in a diff. The API also returns the surrounding `diff_hunk`, so a client can
  present local context while retaining the review location
  ([review comments](https://docs.github.com/en/rest/pulls/comments)).
- Plannotator, Markdown Review, HiNote, and Remark produce readable feedback, Markdown
  exports, or compact agent queues while keeping richer state elsewhere.
  Markdown Review’s omission of most selected source text shows the principal failure
  mode: a line label and comment alone do not give the recipient enough evidence to
  verify the target.

TextRef can support the same pattern without defining another persisted annotation
format.
A context renderer takes canonical sidecar data plus the current source, resolves
every target, derives display coordinates, merges nearby excerpts, and emits plain
Markdown-compatible ASCII. For example:

```text
Document: ./design.md
Source: sha256:83f6d4... (matched)

@@ L41-L45 @@
  41 | The parser normalizes line endings before hashing.
  42 | Canonical source is authoritative.
     | [A1 span L42:C1-L42:C35] "Canonical source is authoritative."
     | [A1 commenting] Define which normalization profile is canonical.
  43 | Derived views are secondary.
     | [A2 point before L43:C1] Add a transition before this sentence.
  44 | Resolution reports ambiguity rather than guessing.
  45 |

Unresolved:
  [A3 ambiguous] "the source" -- 2 candidates; clarification required
```

The format resembles a context diff but does not prefix source lines with `+` or `-`,
because it does not claim that source changed.
Annotation rows have explicit IDs, target kinds, display ranges, motivations, and
bodies.
Edit proposals can add a `replacement` row without mutating the displayed source.

The renderer should follow deterministic rules:

- Use one-based `L` and `C` labels for people and agents; declare that columns count
  Unicode code points, not UTF-16 units, bytes, grapheme clusters, or terminal cells
- Include the matched source lines and enough exact quote to identify every resolved
  span or section anchor; mark size-budget elision explicitly and keep the complete quote in the
  structured sidecar rather than relying on a caret underline as the only evidence
- Render point affinity and the owning context explicitly
- Render a section annotation at its heading with the complete derived line range.
  When the section does not fit the context budget, show separate start and end windows
  with explicit intervening elision rather than printing unrelated document content
- Merge overlapping context windows as diff tools merge nearby hunks, with a
  configurable but reported context-line count
- Sort resolved annotations by source position and then stable annotation ID
- Put whole-document annotations in a document section and missing, ambiguous, and
  orphaned targets in explicit unresolved sections with last-known quotes
- Report source-hash match or mismatch and the resolution method in the header or
  annotation row
- Omit ANSI color by default; color and terminal-cell caret alignment are optional
  presentation layers

This view is context-efficient because unrelated document content is absent, yet every
annotation remains adjacent to enough source for an agent to reason about it.
It is not round-trippable and should not be parsed back into annotations.
The structured sidecar remains authoritative; the context view is regenerated after
source or annotation changes.

### Markdown Diffs and Redlines Belong Above the Reference Layer

A source diff, a redline, and an edit proposal answer different questions:

- A **source diff** compares a base representation with a result representation
- A **redline** displays insertions and deletions together for review
- An **edit proposal** specifies content to insert, delete, or replace

TextRef answers only where an edit applies.
Adding diff or redline semantics to a selector would couple target identity to one
workflow and duplicate formats that already represent changes.
Version 0.1 therefore needs no `DiffRef`, `PatchRef`, or `diff` selector kind.

#### Source Diffs Remain the Primary Change Artifact

For Git-backed Markdown, the repository’s before and after blobs and the Git patch
between them provide the primary review and application workflow.
Git patch output includes paths, blob identifiers, rename or copy metadata, and
line-oriented hunks ([patch format](https://git-scm.com/docs/diff-generate-patch.html)).
It preserves changes to Markdown syntax as well as visible prose, which is necessary
when a link destination, heading marker, code fence, or other source construct changes
without an equivalent plain-text change.

Git already supplies Markdown-aware presentation hooks.
A repository can set `*.md diff=markdown` to enable Git’s built-in Markdown patterns for
hunk headers and word splitting, and `--word-diff` can show changes within lines
([Git attributes](https://git-scm.com/docs/gitattributes),
[word diff](https://git-scm.com/docs/git-diff)). These options improve review output
without changing patch application or merge semantics.
Git’s `--word-diff=porcelain` is intended for scripts, but it remains a derived
word-diff view rather than a persisted edit protocol.

Prose wrapping can still turn a small edit into several changed source lines.
Stable formatting, semantic line breaks, and word-level review can reduce that noise;
they are repository authoring and review policies rather than TextRef semantics.

Rendered comparison is also useful but remains derived.
GitHub offers both source and rendered views for Markdown changes
([prose diffs](https://docs.github.com/en/repositories/working-with-files/using-files/working-with-non-code-files)).
Lowdown’s `lowdown-diff` compares parsed Markdown trees, marks nodes as inserted or
deleted, and can render the result to HTML, terminal text, or other outputs
([diff engine](https://kristaps.bsd.lv/lowdown/diff.html)). Its handling of tables and
metadata is deliberately coarse, illustrating that a syntax-tree diff is a review view,
not a lossless replacement for the source patch.

TextRef should therefore integrate with source diffs rather than define another diff
format. A patch may use its base and context to apply changes, but hunk line numbers and
context are not durable passage identities and must not become TextRef selectors.
Comments on a displayed diff can target the immutable base or result document with an
ordinary TextRef; the review envelope retains the chosen side, revisions, and hunk
presentation.

#### Inline Redline Syntaxes Are Compatibility Formats

CommonMark defines no insertion or deletion syntax.
Several Markdown dialects and adjacent formats add one:

| Format | Change Representation | Compatibility Limit |
| --- | --- | --- |
| GitHub Flavored Markdown | `~~deleted-looking text~~` renders as `<del>` | The specification defines an emphasis type, not a proposed edit, and provides no insertion, base, author, or accept/reject state ([GFM](https://github.github.com/gfm/#strikethrough-extension-)) |
| GitLab Flavored Markdown | `{+ addition +}` and `[- deletion -]` inline diff markers | GitLab-specific display syntax; delimiters cannot be mixed, and inline code requires special handling ([GLFM](https://docs.gitlab.com/user/markdown/#inline-diff)) |
| Raw HTML in Markdown | `<ins>` and `<del>` identify additions and removals; HTML also permits `cite` and `datetime` | CommonMark passes the tags through as raw HTML, while sanitizers and HTML content-model rules limit portability across paragraphs, lists, and tables ([CommonMark](https://spec.commonmark.org/0.31.2/#raw-html), [HTML](https://html.spec.whatwg.org/dev/edits.html)) |
| CriticMarkup | `{++addition++}`, `{--deletion--}`, `{~~old~>new~~}`, highlights, and comments; processors can accept or reject changes | It is a preprocessing layer orthogonal to Markdown. Change delimiters can cross Markdown boundaries, and MultiMarkdown documents cases that do not render as valid HTML ([MultiMarkdown](https://fletcher.github.io/MultiMarkdown-6/MMD_Users_Guide.html#criticmarkup)) |
| Pandoc tracked-change spans | DOCX insertions, deletions, and comments become spans with classes, author, and time | `--track-changes` affects only the DOCX reader, and portability depends on Pandoc’s AST and output dialect ([Pandoc](https://pandoc.org/demo/example2.html#option--track-changes)) |
| Fenced `diff` code block | Displays literal patch text with optional syntax highlighting | A code fence is a presentation container; CommonMark assigns no application semantics to its info string ([CommonMark](https://spec.commonmark.org/0.31.2/#fenced-code-blocks), [GitHub](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-and-highlighting-code-blocks)) |

CriticMarkup is the most complete inline redline compatibility target because it covers
insertions, deletions, substitutions, highlights, and comments and can produce accepted
and rejected documents.
It is not suitable as canonical sidecar state: it edits the Markdown source, has no
document locator or base validator, and interleaves a second syntax with Markdown
parsing. GFM strikethrough is even less suitable because authors also use it as ordinary
presentation.
An importer must not interpret `~~text~~` as a deletion proposal without an
explicit profile declaring that meaning.

Inline `<ins>` and `<del>` and GitLab’s markers have the same distinction.
They can be redline projections, but their presence in source does not prove that an
application should accept or reject a change.
A sidecar should remain authoritative when both a structured edit and an inline
projection exist.

#### Typed Edit Proposals Belong in the Annotation Envelope

The annotation layer can add a discriminated edit body without changing TextRef:

```yaml
format: text-edit-annotation/0.1
id: edit-42
motivations: [editing]
target:
  format: textref/0.1
  document: ./design.md
  source_hash: "sha256:83f6d4..."
  selector:
    type: span
    exact: old wording
    prefix: "The paragraph uses "
    suffix: " here."
    start: 913
body:
  type: text-edit
  operation: replace
  content:
    media_type: text/markdown
    value: clearer wording
```

The three basic operations use existing target shapes:

| Operation | Target | Edit Body |
| --- | --- | --- |
| Insert | `point` selector | Required non-empty source content |
| Delete | Non-empty `span` selector | No replacement content |
| Replace | Non-empty `span` selector | Required source content |

Replacing a whole document can use a TextRef without a selector.
Moves, file renames, and cross-file changes can initially decompose into delete and
insert operations while a future change set retains their logical grouping.

This matches the W3C Web Annotation `editing` motivation, which means a request to edit
the target resource ([vocabulary](https://www.w3.org/TR/annotation-vocab/#editing)). It
also matches SARIF’s structured fix model: a replacement combines a region to delete
with optional inserted content, and a zero-length region represents an insertion point
([SARIF](https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/sarif-v2.1.0-errata01-os-complete.html)).

An edit profile should require a matching base `source_hash` for automatic application.
Quote and context can relocate a stale proposal for review, but re-anchoring alone does
not prove that applying the old replacement remains correct.
After a hash mismatch, the consumer should expose the relocated proposal for
confirmation or regenerate it against the current source.

Workflow state remains separate.
A proposal may be pending, accepted, rejected, or superseded independently of whether
its target is anchored, relocated, ambiguous, or orphaned.
Strikethrough as annotation styling also remains distinct from a delete operation.

#### Atomic Multi-Edit Changes Need a Separate Change Set

Several edits that must apply together need semantics that do not belong in TextRef or a
single annotation:

- One validated base representation for every edit
- Stable ordering for co-located insertions
- Rules for overlaps and dependent edits
- All-or-nothing validation and application
- An optional result hash
- Cross-file grouping when one logical change touches several documents

SARIF addresses this at the fix layer: one fix contains artifact changes, each artifact
change contains replacements, every replacement is located in the unmodified artifact,
and replacement order is explicit.
GitHub and GitLab likewise keep suggested edits in review state and apply one or a batch
by creating a commit
([GitHub suggestions](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/incorporating-feedback-in-your-pull-request),
[GitLab suggestions](https://docs.gitlab.com/user/project/merge_requests/reviews/suggestions/)).

A future `TextChangeSet` can adopt the same separation: a required base TextRef without
a selector for each document, a source hash for each base, an ordered collection of
TextRef-targeted edit operations, and optional result hashes.
The first consumer should define overlap, ordering, and atomicity semantics before this
becomes a portable format.
A separate SnapshotRef remains unnecessary; base hashes validate the coordinate spaces,
while Git or another version store retains historical content.

#### Compatibility Should Be Directional and Explicit

Adapters can support existing workflows without making their formats normative:

1. Export a structured edit or change set by applying it to one verified base in memory,
   then generate a Git patch, rendered diff, CriticMarkup document, or platform-specific
   suggestion.
2. Import a Git patch only with its base representation available.
   Apply or reconstruct the result first, then derive source-grounded edit targets; do
   not translate hunk line numbers directly into selectors.
3. Import CriticMarkup by deriving accepted and rejected source versions and comparing
   them. Reject or preserve constructs whose interleaving with Markdown prevents an
   unambiguous source edit.
4. Treat GFM strikethrough, raw `<ins>/<del>`, and GitLab inline diff as edits only
   under an explicit import profile.
5. Report metadata that a projection cannot preserve, such as threads, status, target
   history, atomic grouping, or source validation.

The resulting ownership is:

| Concern | Status | Owner |
| --- | --- | --- |
| Whole-document, span, point, or section target | First-class in v0.1 | TextRef |
| Single insert, delete, or replace proposal | First-class when an editing profile is defined | Annotation envelope |
| Atomic multi-edit or cross-file change | Deferred until a consumer defines its semantics | Sibling change-set protocol |
| Git/source patch | Existing primary change artifact | Git or source-control adapter |
| CriticMarkup, GLFM, HTML, Pandoc, or rendered redline | Directional compatibility projection | Import/export adapter |

### Standoff Annotation Formats Assume Immutable Text

NLP and digital-humanities standoff annotation is the oldest sidecar tradition, and its
consistent weakness defines the gap this protocol fills: every format assumes an
immutable base text and offers at best integrity validation, never relocation.

- **brat** `.ann` files pair with an unmodified `.txt` by basename and record type,
  start/end offsets, and the referenced text, but the stored text is documented as
  reference-only: it is never used to validate or re-anchor, so edits silently misalign
  every offset. The quote is present but decorative; this protocol makes it load-bearing.
- **WebAnno TSV** documents its offsets as UTF-16 code units, so a single astral
  character (an emoji) shifts every later offset by two.
  This is precisely the cross-language unit bug the canonical source profile must rule
  out by pinning offsets to Unicode code points.
- **STAM** (“stand-off text annotation model”) is the modern formalization: plain UTF-8
  text kept as-is, annotations selecting offsets, with reference validation and a W3C
  Web Annotation exporter.
  It detects breakage but does not heal it.
- **TEI standoff, ISO LAF/GrAF, and UIMA CAS** anchor by pointer or offset into a frozen
  source; Bański’s Balisage analysis of TEI standoff documents how poorly XPointer-based
  structural anchoring is supported in practice, a further argument for text-content
  anchoring over structural paths.
- **Adjacent sidecar precedents** show the same pairing this protocol proposes.
  SARIF static-analysis results carry file-plus-region locations alongside
  `partialFingerprints` (hashes of the code snippet) so findings re-match after lines
  shift; XMP photo sidecars demonstrate that the sidecar-to-asset binding itself is a
  failure surface (rename or edit the asset and the sidecar silently detaches), which a
  source hash detects.
  Line- and diff-anchored review comments (GitHub’s `position`, Gerrit patch sets)
  demonstrate how positional anchors decay: GitHub marks them “outdated” and hides them,
  and Gerrit re-derives positions by diffing revisions, an option unavailable to a
  sidecar that meets only the current document.

### Available Markdown Sidecars Cover Only Part of the Problem

Available formats and systems cover only parts of Google-Docs-style comments on Markdown
stored out of band:

- **Inline syntaxes change the document.** CriticMarkup (`{>>comment<<}`,
  `{==highlight==}`) keeps anchors beside their content because the markers live in the
  text, but it adds annotation syntax to content diffs, renders as unsupported markup in
  tools that do not recognize it, and carries no threading or resolution model.
  HTML comments and Obsidian `%%` comments share the problem.
  iA’s Markdown Annotations spec (v0.2) appends an annotation block to the file anchored
  by grapheme-cluster offsets plus a SHA-256 hash; the hash detects edits but nothing
  repairs the offsets.
- **Hosted commenting systems do not export portable annotation state.** HackMD,
  StackEdit, GitBook, and Google Docs all offer selection-anchored threads, and none
  produces a portable artifact next to the Markdown.
  Google Docs is instructive: comments ride the internal revision history, the Drive API
  documents comment anchors as immutable and revision-bound with no positional guarantee
  between revisions, and the 2024 native Markdown import/export carries content only, so
  comments do not survive the round trip.
  Edit-history anchoring works only inside the system that recorded the edits.
- **CRDT anchors depend on the originating data model.** Peritext (Ink and Switch)
  anchors comment spans to stable per-character operation IDs with tombstones, so
  anchors never dangle inside the CRDT, and ProseMirror, Yjs, and Automerge each provide
  positions that transform through edits.
  These positions remain durable within the originating data model, but a plain Markdown
  file on disk has no operation IDs.
  Content-based re-anchoring is the only option for files edited by arbitrary tools,
  which is exactly the situation of a git-tracked document edited by people and agents.
- **MRSF (“Sidemark”) provides a direct packaging precedent.** The 2026
  single-maintainer Markdown Review Sidecar Format stores threaded, resolvable comments
  in a `<doc>.md.review.yaml` sidecar with JSON Schema, a command-line interface (CLI),
  a Model Context Protocol (MCP) server, and VS Code tooling
  ([spec](https://github.com/wictorwilen/MRSF)). Its anchors store line/column
  coordinates, the selected text (with a SHA-256 hash of that selection), and an
  optional git commit for staleness; re-anchoring falls back from exact text match
  through line/column plausibility to contextual search, ending in an explicit orphaned
  state. MRSF demonstrates the sidecar packaging and differs from TextRef in three
  relevant ways: it has no prefix/suffix context to disambiguate duplicate quotes, ties
  staleness detection to git commits rather than a normalized document hash, and uses
  line/column coordinates rather than text offsets as positional evidence.
- **Agent-oriented systems provide related examples.** Semiont (AI Alliance) stores dual
  selectors per annotation (quote plus position), reconciles them at write time,
  re-anchors on verbatim quote match with context recovery, and flags failures
  low-confidence instead of guessing.
  Codetations (2025) keeps notes out-of-document and combines edit-tracking while an
  editor is live with LLM-assisted re-anchoring for offline edits, and reports that
  anchored annotations improve LLM code-repair performance.
  Agent-facing Markdown review tools available in 2025 and 2026 (md-annotator,
  md-review, and Google-Docs automation workarounds for the Drive API anchor limitation)
  provide further examples of demand for a portable, content-anchored comment format.

### Plannotator Separates Product State From Portable Sharing

Plannotator release `v0.23.1` at commit
[`29513e19`](https://github.com/backnotprop/plannotator/tree/29513e1984805a582e644b192b82a8d9cec31943)
is an agent-facing review tool for plans, documents, and code changes.
Its tradeoffs provide implementation evidence, but its private runtime shapes do not
form an interchange standard.

There is no single Plannotator annotation format.
The repository contains several related representations optimized for different
lifetimes:

| Layer | Representation | Purpose and Lifetime |
| --- | --- | --- |
| Plan/document UI | `Annotation` object | In-memory annotation and crash-recovery state |
| Code review UI | `CodeAnnotation` object | Diff-line, file, or review-scoped feedback |
| Draft storage | Versionless JSON keyed by content hash | Best-effort local crash recovery |
| Share links | Compressed compact `SharePayload` | Portable plan plus annotations |
| External API | JSON requests plus SSE events | Session-local tool integration |
| Agent feedback and archive | Rendered Markdown | Human/agent consumption, not round-trip import |

#### Plan and Document Anchors

The plan/document
[`Annotation`](https://github.com/backnotprop/plannotator/blob/29513e1984805a582e644b192b82a8d9cec31943/packages/ui/types.ts)
contains:

- `originalText`, the selected rendered text
- optional `startMeta` and `endMeta` DOM endpoint records, each containing a parent tag,
  the parent’s ordinal among elements with that tag, and a text offset
- legacy ordinal `blockId`, `startOffset`, and `endOffset` fields
- an action type (`COMMENT`, `DELETION`, or `GLOBAL_COMMENT`), optional comment body,
  author, images, quick-label metadata, and source-tool metadata
- special exact TeX plus block-ID targets for rendered mathematics

The block parser assigns sequential IDs such as `block-0`, so inserting or reparsing a
preceding block changes later IDs.
The DOM metadata is likewise representation-specific and positional: it identifies, for
example, a character in the fourteenth rendered paragraph rather than a passage in
Markdown source. Both are useful fast paths within one rendering, not durable identity.

The
[`useAnnotationHighlighter`](https://github.com/backnotprop/plannotator/blob/29513e1984805a582e644b192b82a8d9cec31943/packages/ui/hooks/useAnnotationHighlighter.ts)
recovery cascade is:

1. Find special math targets by block ID and exact TeX.
2. Restore the DOM endpoints when present.
3. Search the complete rendered text for `originalText`, first literally and then with
   collapsed whitespace and selected renderer transformations.
4. If no match exists, retain the annotation in the panel without an inline mark.

The general viewer leaves content verification of a successful DOM restore disabled by
default. An opt-in mode verifies the painted text, removes a mismatched mark, and tries
text search. The text fallback always returns the first occurrence; it has no
prefix/suffix context or ambiguity outcome, so repeated text can attach to the wrong
passage. When Plannotator’s editor changes Markdown, it mitigates the risk by discarding
stale DOM metadata and relocating an annotation to the first parsed block containing
`originalText`. That is a product-specific tradeoff, not edit-robust anchoring.

Raw-HTML annotation is even more deliberately portable-by-quote.
DOM node paths are used only while a selection is live; the stored annotation retains
`originalText`, and restoration marks the first exact occurrence in the rendered HTML.
Neither plan nor HTML annotations support zero-width point targets.

#### Sharing Format

The compact
[`SharePayload`](https://github.com/backnotprop/plannotator/blob/29513e1984805a582e644b192b82a8d9cec31943/packages/ui/utils/sharing.ts)
is the closest Plannotator comes to an interchange format:

```ts
interface SharePayload {
  p: string;                 // Markdown plan
  a: ShareableAnnotation[];  // Compact tuples
  g?: ShareableImage[];
  d?: (string | null)[];     // Parallel diff-context array
  s?: (string | undefined)[];// Parallel producer-source array
  h?: string;                // Raw HTML
  r?: 'html';
}
```

Annotation tuples use `D`, `C`, or `G` discriminators for deletion, comment, or global
comment. They preserve the selected rendered text, body, author, images, and quick-label
flag, but deliberately omit IDs, timestamps, block IDs, offsets, DOM endpoints, math
targets, and source-document identity.
An importer creates new IDs and re-anchors from the quote.
Two peers can therefore exchange useful feedback, but not the identity or full anchoring
evidence of the original annotation.

The payload has no format/version field.
It supports optional tuple members, both legacy string images and image tuples, and
parallel arrays keyed by annotation index.
This achieves small URLs but makes schema validation and independent evolution harder.
TextRef should keep its explicit version, structured objects, named fields, and
namespaced extension container rather than copy this compression-oriented layout.

Small shares store `deflate-raw(JSON)` as base64url in the URL fragment.
Large shares encrypt that compressed string with AES-256-GCM, upload only ciphertext,
and put the key in the fragment.
This separates the logical payload from compression, encryption, and storage.
It argues that confidentiality and compact transport encodings should wrap TextRef and
annotation objects rather than change their data model.

#### Drafts, External Events, and Archives

Plannotator drafts store the full UI objects in JSON files under
`~/.plannotator/drafts`. The filename key is the first 16 hexadecimal characters of
SHA-256 over the exact plan or diff content.
The hash prevents a draft from loading against different input, but it is not persisted
as annotation evidence and cannot re-anchor after an edit.
This independently validates `source_hash` as a small validator field rather than a
snapshot object.

Draft writes use atomic rename, monotonically increasing `draftGeneration`, and
generation tombstones so a delayed autosave cannot resurrect deleted feedback.
Those are valuable sidecar synchronization semantics, but they belong to an annotation
container or event log, not TextRef.

The external-annotation API accepts session-local JSON and broadcasts `snapshot`, `add`,
`remove`, `clear`, and `update` events over Server-Sent Events (SSE). Plan inputs use
`originalText`; the agent instructions explicitly tell producers to pick a unique
rendered substring. Code-review inputs instead use a discriminated `line`, `file`, or
`general` scope with a file path, line range, old/new side, optional selected code, and
optional replacement.
The explicit scope is useful, although internal empty-path and zero-line sentinels show
why a wire schema should encode variants structurally.
The API’s `source` means producing tool, not target document, which is another reason
for the annotation envelope’s less ambiguous `provenance.system` name.

Code annotations can also retain token text and character offsets, PR URL and scope, or
the commit SHA whose diff supplied the line numbers.
Plannotator emits explicit export warnings when an annotation is viewed under a
different commit diff, demonstrating that a line range is meaningful only with its
representation identity.
TextRef’s DocRef and optional source hash provide the analogous binding for source-text
annotations.

On submission, Plannotator renders annotations to Markdown such as
`Feedback on: "<quote>"` or file/line headings and sends that prose to the agent.
Saved plan decisions append the rendered feedback after a thematic break; status lives
in the filename. These artifacts are readable operational outputs, but they discard the
machine-readable annotation objects and are not intended for round-trip import.

#### Design Lessons From Plannotator

Plannotator reinforces the proposed boundaries:

- Keep the exact quote, but add independent context, position, and optional source-hash
  evidence so repeated text is not resolved by first match.
- Treat rendered Markdown and source Markdown as different representations.
  Plannotator’s `originalText` is rendered text; it cannot be used as source
  `selector.exact` without an adapter.
- Keep structural and DOM endpoints as optional adapter hints, never as the only anchor.
- Preserve explicit missing and ambiguous outcomes.
  A panel-only orphan is safer than a wrong inline highlight, and a first-match fallback
  should not silently claim success.
- Version portable formats and prefer named objects over compact tuples and parallel
  arrays. Compression belongs in an optional transport projection.
- Keep annotation intent and bodies outside TextRef.
  Plannotator’s comments, redline deletions, quick labels, replacement code, images, and
  producer metadata fit an extensible envelope with motivations such as `commenting`,
  `editing`, and `classifying`.
- Keep autosave generations, tombstones, live events, identity, and encryption outside
  the target reference.
- Add a point selector explicitly; neither empty/global comments nor whole-element
  pinpoint selection represents a stable zero-width boundary.

A directional adapter should map fields by meaning, not by similar spelling:

| Plannotator Evidence | TextRef or Envelope Treatment |
| --- | --- |
| Rendered `originalText` | `captured_text`, or a rendered-text selector; only an adapter may derive source `exact` |
| DOM `startMeta`/`endMeta` | Namespaced representation-specific hint, never core evidence |
| Ordinal `blockId` and offsets | Discard or retain as adapter hints; do not treat as stable structure |
| `COMMENT`, `DELETION`, `GLOBAL_COMMENT` | Envelope motivations/body; global comment targets the whole document |
| Annotation `source` producer | `provenance.system`, not TextRef `document` |
| Draft content-hash key | Recompute a full qualified `source_hash` from canonical source when available |
| Code file/line/side or commit-diff fields | A future diff representation adapter, not a source-text selector |

### Markdown Review Is a Transactional Block-Review Tool

Markdown Review at commit
[`149fe77`](https://github.com/rwoll/markdown-review/tree/149fe77c44645d16db4ba9689bde4952056404a6),
one commit after its `v0.0.9` tag, is a small TypeScript/Preact monorepo whose core
review UI is embedded in web, CLI, VS Code, and Copilot-plugin surfaces.
Its interaction model lets reviewers click whole rendered Markdown blocks, leave
comments, answer questions embedded by an agent, add general notes, and send readable
Markdown feedback back to that agent.

There is no durable Markdown Review annotation format.
The product has three short-lived representations:

| Layer | Representation | Lifetime |
| --- | --- | --- |
| Parsed document | Top-level `Element[]` with type, plain content, and zero-based line range | One rendering |
| Review state | In-memory maps keyed by element index or question ID | One UI session |
| Agent handoff | Generated Markdown, optionally wrapped as `{ "feedbackMarkdown": "..." }` | One-way output |

#### Block Targets and Session State

The
[`extractElements`](https://github.com/rwoll/markdown-review/blob/149fe77c44645d16db4ba9689bde4952056404a6/packages/core/src/extract-elements.ts)
parser flattens top-level headings, paragraphs, block quotes, tables, thematic breaks,
code blocks, and individual list items into elements containing rendered plain text and
zero-based start/end lines.
The renderer independently parses the Markdown again, maps each rendered node’s source
start line to an element index, and exposes a clickable DOM block such as `el-7`.

An inline annotation is only `{ note, time }` stored under that numeric element index.
The target is implicit in the map key.
This has several consequences:

- The unit of annotation is a whole rendered block.
  There are no substring highlights, exact quotes, ranges, point targets, colors, target
  IDs, threads, or multiple comments on one block; saving another comment under the same
  index replaces the first.
- Element order and source lines are sufficient only because the document is fixed for
  the review transaction.
  They are not stable identities after insertions or parser changes.
- General notes are correctly modeled as whole-document feedback rather than as fake
  inline targets.
- State is not persisted to local storage or a sidecar.
  `PlanReview.init` clears it, and the VS Code custom editor rebuilds the webview when
  the document changes.
  The product therefore resets review state instead of re-anchoring it after an edit.

This simplification works for a single review transaction but does not support a
portable reference format.
A whole-block comment needs no new selector type: a Markdown adapter can create a normal
`span` selector over the block node’s complete source span.
An element index, node type, heading path, or parser ID may remain a namespaced
fast-path hint, but the target should retain source quote, context, position, and
optional source hash evidence.

#### Feedback Markdown Is a Projection, Not an Interchange Schema

The
[`buildFeedbackMarkdown`](https://github.com/rwoll/markdown-review/blob/149fe77c44645d16db4ba9689bde4952056404a6/packages/core/src/components/NotesPanel.tsx)
function exports headings and fenced metadata containing the file name, `Lstart-Lend`,
element type, and comment.
Only code annotations include a source snippet, limited to the first three lines.
Comments on paragraphs, headings, lists, block quotes, and tables omit the selected
content entirely. After line movement, a record such as `PLAN.md:L2-L2` has neither a
durable anchor nor enough quoted evidence for a person or agent to verify the intended
passage.

The line labels also expose the model’s zero-based values directly.
The checked-in feedback snapshot says `L2-L2` for a fixture paragraph on source line 3.
This is a concrete example of why line/column coordinates must declare their base and
unit, and why human line labels should be derived from a resolved source range rather
than serve as the only stored target.

The browser sends only `{ "feedbackMarkdown": generatedMarkdown }`. The CLI’s `--json`
flag pretty-prints that wrapper; it does not emit structured annotations or question
responses.
The export is useful agent-facing prose, but cannot be validated, re-anchored,
merged, or round-tripped as annotation data.
TextRef consumers should instead retain a versioned structured sidecar as the canonical
record and generate Markdown, terminal text, or compact transport forms as disposable
projections.

#### Embedded Questions Provide a Useful Extension Pattern

Markdown Review recognizes `question:open`, `question:choice`, and `question:checkbox`
fenced code blocks.
Each has an author-supplied `id`, prompt, and optional pipe-separated
choices; answers are text, one choice, or several choices keyed by that ID. This
demonstrates two useful concepts outside the TextRef core:

- An authored semantic ID can be a strong structural hint for an interactive object.
  An adapter should validate that IDs are non-empty and unique; Markdown Review’s parser
  defaults missing IDs to an empty string and does not reject duplicates, so answers can
  collide.
- Annotation bodies can evolve through a discriminated union such as plain text, single
  choice, and multiple choice without changing the target reference.

For portability, an answer can target a `span` selector over the question block’s full
Markdown source span, use `replying` as its motivation, and keep the question ID under a
profile-defined field or namespaced extension.
The ID helps find the object, while the source quote and optional hash detect a reused
ID or changed prompt.
Version 0.1 of the small annotation envelope can remain text-body-only; typed response
bodies are an additive future profile rather than a reason to generalize TextRef.

#### Design Lessons From Markdown Review

Markdown Review reinforces and sharpens the proposed design:

- Treat element indices and line ranges as ephemeral UI coordinates, not identities.
- Represent whole-block annotations as ordinary source spans; do not add a `block`
  selector merely to mirror one product’s interaction granularity.
- Always retain the complete exact source quote for an anchored comment.
  A display projection may truncate it, but the canonical record must not.
- Keep structured annotation data separate from readable agent feedback.
  Calling a Markdown string inside JSON “structured feedback” does not make it
  round-trippable.
- Give annotations independent IDs and store them as a collection so one target can have
  multiple comments or a thread.
- Validate semantic IDs before using them as keys, and corroborate them with source
  evidence when content may change.
- Keep line-number presentation explicitly separate from TextRef’s zero-based Unicode
  code-point offsets.
- Treat edits during an active review as a real lifecycle event: re-anchor or visibly
  orphan existing targets instead of silently resetting or reassigning them.

A directional adapter is straightforward:

| Markdown Review Evidence | TextRef or Envelope Treatment |
| --- | --- |
| File name | Resolve to a DocRef using the invoking consumer’s base |
| Element index and `el-N` DOM ID | Discard after using the parsed node to construct a source selector |
| Zero-based line range | Adapter hint only; derive display lines from the resolved source range |
| Element `content` | `captured_text`; it is rendered/plain text, not necessarily source `exact` |
| Full parsed block source span | Construct `selector.exact`, context, and `start` from canonical Markdown |
| Inline `note` | Annotation text body with `commenting` motivation |
| General note | Whole-document annotation with no selector |
| Question ID and typed answer | Profile metadata plus `replying` body; validate and bind to the question source span |
| Generated feedback Markdown | Non-normative output projection |

### HiNote Implements Contextual Recovery for In-Band Highlights

CatMuse HiNote release `0.5.7` at commit
[`49f6753`](https://github.com/CatMuse/HiNote/tree/49f6753725e2af9763fd50ff2633b18be9bcc5b0)
is an Obsidian plugin that finds highlights already marked in Markdown with `==...==`,
`<mark>`, `<span>`, or a user-defined regular expression.
It stores comments outside the document under `.hinote`, displays them beside the
in-band highlights, and can export highlights and comments as callout-based Markdown.

HiNote is the closest implementation described here to the proposed sidecar lifecycle.
Its matcher combines text and position with two-sided context and fuzzy scoring.
This provides implementation evidence, although its private schema and algorithms are
not a portable format.

#### Persisted Highlight and Comment Shape

Each source file has a versioned JSON record under `.hinote/highlights`, while a
separate mapping file associates vault paths with storage filenames.
The persisted version 2.0 shape is approximately:

```json
{
  "version": "2.0",
  "lastModified": 1789092000000,
  "highlights": {
    "highlight-193428019-42": {
      "text": "independent evidence",
      "position": 42,
      "created": 1789091000000,
      "updated": 1789092000000,
      "backgroundColor": "#ffeb3b",
      "blockId": "optional-structural-hint",
      "contextBefore": "anchors need",
      "contextAfter": "to survive edits",
      "textFingerprint": "independent evidence",
      "comments": [
        {
          "id": "comment-1789091000000-j5z7v3q2a",
          "content": "Compare this with quote matching.",
          "created": 1789091000000,
          "updated": 1789091000000
        }
      ]
    }
  }
}
```

This captures several consumer choices relevant to a portable design:

- Highlights and comments have independent IDs and timestamps.
- One target can own several comments without overwriting existing comments.
- Highlight color is presentation metadata rather than part of target matching.
- File-level comments use the same comment UI while remaining conceptually distinct from
  text highlights.
- The storage object has an explicit version and validates required field types.

It also mixes layers that TextRef should keep separate.
The target evidence (`text`, position, context, and block ID), annotation style and
cloze flags, comment bodies, and storage bookkeeping share one object.
The field called `textFingerprint` is whitespace-normalized text, not a digest or an
algorithm-qualified fingerprint.
Names should expose that distinction: normalized matching text is selector evidence; an
actual `source_hash` verifies the complete canonical source.

HiNote derives a highlight ID from file path, position, and text using a 32-bit string
hash.
That value is deterministic for an unchanged extraction but changes after a rename,
offset shift, or text edit, so it is a useful fast-path key rather than durable
identity. TextRef annotations should use opaque annotation IDs independent of mutable
target evidence.

#### Matching Cascade and Fuzzy Recovery

The
[`findStoredHighlightMatch`](https://github.com/CatMuse/HiNote/blob/49f6753725e2af9763fd50ff2633b18be9bcc5b0/src/services/highlight/HighlightMatchStrategies.ts)
cascade compares a current in-document highlight with stored comment targets:

1. Exact generated ID
2. Matching block ID plus exact text, or sufficient context for the only block candidate
3. Exact text at the nearest stored position within 500 JavaScript string units
4. A weighted context score using block agreement, proximity, two-sided context, and
   bigram Dice similarity for normalized text
5. Exact text when only one stored candidate has that text

The context tier requires a score of at least 1.35 and rejects the result when the
runner-up is within 0.2. It also requires either position within 1,200 units or strong
context on both sides.
These concrete thresholds validate the proposed extensibility model: the persisted
evidence does not need to change when an application adds a named fuzzy policy with an
absolute threshold, runner-up margin, proximity, and independent corroboration.

The implementation also shows why those policies must be specified and tested:

- The repository contains no automated tests or edited-document corpus for the matching
  thresholds, duplicate behavior, Unicode offsets, or false attachments.
- The exact-text/position tier chooses the closest candidate without a runner-up check.
- Matching is greedy across current highlights.
  A `usedIds` set prevents one stored record from attaching twice, but a repeated
  current passage processed first can claim the only stored record even when the
  reference is ambiguous.
- A context match is labeled with a method but the score, runner-up, rejected evidence,
  and candidates are not returned to the caller.
- After an ID, block, text-position, or fuzzy context match, HiNote automatically
  rewrites stored text, position, context, and fingerprint evidence.
  A false fuzzy attachment can therefore erase the evidence needed to recover the
  original target later.

TextRef should preserve its conservative contract: exact methods may refresh position
evidence, while normalized or fuzzy methods return candidates and method-specific scores
without rewriting the selector until a person or high-assurance policy confirms the
target.
Batch resolution must not use iteration order or an assumed one-to-one assignment
to turn an individually ambiguous reference into a match; several annotations may
legitimately share one target.

#### Coordinate and Representation Mismatches

HiNote’s extractor records `RegExp.exec().index`, so `position` and lengths are
zero-based UTF-16 code units.
For `==selected text==`, the position points to the first `=` while `text` contains only
the inner capture. The stored quote therefore does not equal the source slice beginning
at the stored position.
Context is captured outside the complete marked form and then whitespace-normalized and
trimmed, so it is not literal adjacent source context either.

These choices work inside one JavaScript plugin because the extractor and matcher share
the same assumptions.
They are unsafe as an interchange contract.
A source adapter must choose one actual source range, make `selector.exact` equal that
range, capture literal adjacent prefix and suffix, and convert UTF-16 positions to the
protocol’s Unicode code-point offsets.
For an `==...==` highlight, an adapter can target the inner source text with the opening
and closing markers in adjacent context, or target the complete marked source.
It must declare the choice.
HTML and custom-regex highlights need the same explicit source-versus-rendered-text
decision.

HiNote’s optional Obsidian block ID identifies a containing paragraph, not the precise
highlight. Exports can create such an ID by editing the source document when a
block-reference template requests one.
This supports structural scope as optional corroborating evidence, especially for
repeated quotes, but not as a replacement for quote and context.
Creating structural IDs should remain an explicit source-edit operation rather than a
side effect of resolving or serializing a TextRef.

#### Orphans, Document Notes, and Export

HiNote detects orphaned records by asking whether each stored highlight’s exact text
appears among currently extracted highlights.
Its cleanup operation deletes unmatched records and their comments.
That is appropriate only as an explicit destructive maintenance action; a portable
sidecar should retain unresolved selectors, bodies, and evidence in a visible orphaned
state. The same separation matters for source edits: HiNote’s highlight-removal fallback
can remove the first matching marked text when positional lookup fails, while
TextRef-based editing should require source validation or an exact unambiguous
resolution.

A document-level HiNote comment is stored as a `virtual` highlight with position zero,
placeholder text, and a synthetic block ID. The UI behavior maps directly to a
whole-document target, so the fake anchor is unnecessary.
It maps directly to a TextRef with no selector and a `commenting` annotation body.

HiNote’s Markdown export preserves highlight text, flat comments, and timestamps, and
can include an Obsidian block reference.
Like the other agent and note tool exports described here, this is a readable projection
rather than a round-trippable annotation schema.
Arbitrary CSS colors and custom-regex provenance should be preserved in namespaced
annotation extensions when they do not fit the small portable style vocabulary.

#### Design Lessons From HiNote

| HiNote Evidence | TextRef or Envelope Treatment |
| --- | --- |
| Vault file path and mapping | Consumer-resolved DocRef; rename synchronization stays in the container |
| Inner highlight `text` | Source `exact` only after an adapter identifies its actual range; otherwise `captured_text` |
| UTF-16 marker-start `position` | Convert to a code-point start for the chosen exact source range |
| `contextBefore` and `contextAfter` | Preserve literal adjacent source context in exact-v1; normalized copies are resolver inputs, not replacements |
| Normalized `textFingerprint` | Rename as normalized matching text or omit; it is not `source_hash` |
| Obsidian `blockId` | Optional namespaced structural-scope hint |
| `backgroundColor` | Annotation style; preserve arbitrary CSS under a namespaced extension |
| `comments[]` | Independent annotation bodies or a consumer-owned target group |
| `isVirtual` file comment | Whole-document annotation with no selector |
| `isCloze` and flashcard links | Consumer profile or namespaced annotation extensions |
| Match confidence and scores | Typed resolution method, candidates, algorithm version, and method-specific score |
| Markdown callout export | Non-normative display/export projection |

### Remark Separates Workflow Status From Anchor Quality

Remark is a commercial native macOS Markdown review app.
The product site, bundled skill, and signed release `2026.4.0`, published 26 June 2026,
describe a Swift app with a local MCP server, a bundled CLI, folder review, comment
history, and explicit orphan handling.

No application source or published JSON Schema is publicly available.
The public
[`homebrew-tap`](https://github.com/mfreiwald/homebrew-tap/blob/ebb3abd54f499e5dc6383d1e478b80b277fcef2b/Casks/remark.rb)
states that the application repository is private.
The available evidence has three levels:

- The [product site](https://getremark.app/) and
  [Reddit launch post](https://www.reddit.com/r/ClaudeAI/comments/1rdfag6/i_built_a_markdown_annotation_tool_that/)
  document user-visible behavior.
- The public Homebrew cask, update feed, and bundled installable agent skill document
  the intended CLI and MCP contract.
- Static metadata in the signed
  [`2026.4.0` distribution](https://updates.getremark.app/stable/2026.4.0/Remark.dmg)
  reveals implementation fields and storage concepts, but those are not a supported
  interchange contract.

The signed distribution’s checksum matches the public cask.
Static inspection does not launch or modify the application, bypass licensing, or access
user data.

#### Agent Workflow

Remark runs a bearer-token-protected MCP server on localhost.
Its CLI either calls that HTTP server or acts as a stdio MCP proxy.
The current bundled skill exposes three operations, each scoped to one absolute file
path:

- `list_comments(file_path, status?, anchor_state?)`
- `set_comment_status(file_path, comment_id, status)`
- `export_review(file_path, include_history?)`

The equivalent CLI commands are `remark cli list`, `remark cli status` or its `resolve`
shortcut, and `remark cli export`. The separate `remark open` command deep-links into a
file or folder, optionally filters visible statuses, and focuses one comment.

The skill prescribes a useful deterministic loop:

1. List `unresolved` comments, then `needs_clarification` comments.
2. Process `anchored` targets first, `relocated` targets next, and `orphaned` targets
   last.
3. Read the comment body and active anchor, then edit the Markdown file.
4. Mark a comment `fixed` only after a concrete edit; use `needs_clarification` when the
   request is blocked or ambiguous.
5. Re-list both queues until empty or intentionally deferred.
6. Export a final review, optionally including history, and reopen the file for human
   verification.

This is more precise than a one-shot “send feedback to agent” workflow.
It treats annotations as a review queue with explicit human-visible completion and
supports an agent handing uncertain work back without deleting or falsely resolving it.

#### Observable Agent JSON

The exact nesting is not published as a schema, but the bundled skill and CLI’s
observable coding keys establish the following fields:

| Layer | Observable Fields or Values |
| --- | --- |
| Review/file | Absolute `file_path`; `content_sha256` in exported state |
| Comment | `comment_id`, `body`, `status`, `anchor_state`, `updated_at` |
| Workflow status | `unresolved`, `needs_clarification`, `fixed` |
| Anchor state | `anchored`, `relocated`, `orphaned` |
| Active evidence | `active_anchor` |
| Orphan/history evidence | `last_known_anchor`; optional `history` |
| Anchor | `version`, `selected_text`, UTF-16 start/end offsets, source line/column range, `matcher`, `confidence` |
| Matcher | `exact_offset`, `exact_context`, `fuzzy`, `manual` |
| History event | `event_type`, `actor`, `created_at`; actors include `user`, `agent`, and `system` |

`list_comments` returns a compact queue containing the comment ID, both states, body,
update time, and active anchor.
`export_review` adds the last-known anchor and optional event trail.
The CLI can emit machine-readable JSON and filter independently by workflow or anchor
state.

The static application metadata indicates a local SQLite store with separate file
revisions, comments, anchor versions, and comment events.
File revisions retain a content SHA-256 and byte length.
Anchor versions retain selected text, selected-text and context hashes, two-sided
context, UTF-16 offsets, line data, matcher, confidence, an active flag, and a link to a
file revision. Distinct fields separate source selected text, source context, and source
coordinates from other selection coordinates.
This is evidence of the implementation’s design, not a portable database schema.

Several format questions remain unanswerable from public artifacts:

- Whether `content_sha256` hashes raw bytes or normalized source text
- Exact context construction and fuzzy-matching algorithms or thresholds
- Offset and line/column base conventions beyond the explicitly named UTF-16 offsets
- Whether JSON field additions have compatibility guarantees
- Whether the export has a top-level format/version discriminator

An adapter must not assume those semantics merely because similarly named TextRef fields
exist.

#### Anchor History Avoids Destructive Rewrites

Remark’s public contract names four resolution methods and three anchor-quality states.
An exact unchanged position remains `anchored`; a recovered target becomes `relocated`;
an unresolvable target becomes `orphaned` rather than disappearing.
The GUI warns separately when nearby text moved and when the selected text itself
changed.

The `last_known_anchor` field and optional anchor and event history preserve recovery
evidence. When a target moves, the implementation can create another anchor version and
retain the prior evidence instead of overwriting it in place.
When a target becomes orphaned, the agent still receives the last known quote and
location. This lifecycle preserves more recovery evidence than HiNote’s automatic fuzzy
rewrite and cleanup, and it keeps historical evidence outside the active TextRef.

The design does not require a separate SnapshotRef.
A file revision’s content hash validates the coordinate space used by one anchor
version; version history belongs to the annotation container.
The portable target can remain `document + optional source_hash + selector`, while an
envelope optionally retains prior targets and resolution events.

Remark also demonstrates why workflow state must remain orthogonal to target state.
An orphaned comment can remain unresolved, a relocated comment can be fixed after a
verified edit, and a hash mismatch must never imply completion.
The skill explicitly forbids marking a comment fixed without a real file change.

#### Design Lessons From Remark

Remark’s intended agent interface maps cleanly to the proposed composition:

| Remark Evidence | TextRef or Envelope Treatment |
| --- | --- |
| Absolute `file_path` | Resolve to a DocRef; absolute local paths are not portable by themselves |
| `content_sha256` | Potential `source_hash` only after its input profile is confirmed |
| `selected_text` | `selector.exact` only when it is canonical source text; otherwise `captured_text` |
| UTF-16 offsets | Convert to Unicode code-point offsets in a representation adapter |
| Source line/column fields | Derived presentation or adapter evidence, with explicit bases |
| `matcher` and `confidence` | Typed resolution method and algorithm-specific score, not selector identity |
| `anchored`, `relocated`, `orphaned` | Selector-resolution axis |
| `unresolved`, `needs_clarification`, `fixed` | Annotation workflow axis |
| `active_anchor` | Current target TextRef |
| `last_known_anchor` | Envelope/container recovery evidence when no active target resolves |
| Anchor versions and event history | Optional annotation history, not fields inside TextRef |
| `comment_id` and body | Annotation identity and text body |
| `list_comments` filters | Agent work-queue projection |
| `export_review` | Versioned consumer export should be specified separately from TextRef |

The workflows suggest several concrete requirements for an agent-oriented sidecar:

- Query workflow status and anchor quality independently.
- Preserve orphaned comments and last-known evidence.
- Append confirmed target revisions rather than erasing old evidence.
- Record whether a person, agent, or system changed status or anchoring.
- Require an explicit edit or human decision before moving work to a completed state.
- Let an agent return ambiguous work through `needs_clarification` without inventing a
  target or silently dropping the request.
- Keep the authoritative structured record separate from compact queue views, final
  exports, MCP tools, and GUI deep links.

Within the evidence base, no format combines a document locator, an optional normalized
source validator independent of any version-control system, and a quote-primary selector
with defined re-anchoring in a diffable sidecar.
HiNote comes closest to the selector evidence and recovery cascade, while Plannotator
and Markdown Review provide readable review projections.
Remark adds the strongest workflow and anchor-history model, but its JSON contract is
unpublished, its document locator is an absolute path, and its persisted store is
application-private.
None provides a published, portable, representation-explicit structured anchor through
export and subsequent edits.
Each piece exists separately; the composition does not, which is the case for defining
it once as a protocol.

## Design Requirements

The protocol should meet these requirements:

1. **Small:** Three public reference concepts, four target kinds, one compact JSON
   shape, and a narrow pure API.
2. **Composable:** Whole-document, span, point, and section references use the same top
   level.
3. **Source-grounded:** v0.1 selects one precisely defined Unicode source stream.
4. **Verifiable:** An optional source hash can verify the selector coordinate space.
5. **Durable:** Quotes and boundary context can recover selections after positions move.
6. **Conservative:** Ambiguity is reported rather than guessed.
7. **Cross-language:** Python and TypeScript produce identical normalized forms,
   digests, offsets, and outcomes.
8. **Human-usable:** DocRefs remain compact strings; TextRefs have readable JSON, YAML,
   and URI projections.
9. **I/O-independent:** Parsing and selection do not perform filesystem or network
   access.
10. **Extensible without looseness:** Versioned schemas distinguish supported evolution
    from misspelled fields.
11. **Operation-neutral:** A target reference does not change shape when a consumer uses
    it for a comment, highlight, edit, diff, or redline.
12. **Layered exports:** Persisted objects, sidecars, links, and contextual review views
    have explicit conversion and authority boundaries.
13. **Line-friendly without line fragility:** Consumers can construct and display
    one-based line references without making line numbers durable selector identity.
14. **Structure only when requested:** Spans remain valid at arbitrary source
    boundaries; section and future structural targets declare their parsing profile and
    do not make every TextRef parser-dependent.

## Comparison Matrix

| Approach | Compact | Cross-Tool | Source-Validated | Durable Passage | I/O-Independent | Main Problem |
| --- | --- | --- | --- | --- | --- | --- |
| Keep types inside tbd and FlexDoc | Yes | No | Partial | Partial | Yes | Semantics and fixes drift |
| Adopt full W3C Web Annotation | No | Yes | Via states | Yes | Yes | Too broad and JSON-LD-heavy |
| Make a URI or document fragment the data model | Superficially | Limited | Awkward | Awkward | Yes | Media-type conflicts, escaping, and weak evolution |
| Use only content-addressed identifiers | Moderate | Yes | Yes | No | Usually | Cannot locate mutable/current sources or re-anchor passages |
| Prove, then extract TextRef | Yes | Yes | Yes | Yes | Yes | Requires staged adoption |

## Design Options

### Option A: Keep DocRef and SpanRef in Their Current Projects

**Description:** tbd owns DocRef, FlexDoc owns SpanRef, and applications compose them ad
hoc.

**Advantages:**

- No new repository or release process
- Minimal immediate migration
- Each project can evolve independently

**Disadvantages:**

- No shared top-level reference or source-validation contract
- TypeScript and Python behavior can diverge
- tbd cannot reuse SpanRef without depending on a larger Python document library
- FlexDoc would need to duplicate or depend on tbd’s TypeScript-specific DocRef logic
- Cross-tool persisted references have no independent owner

This remains reasonable only if the two systems never exchange references.
Their planned annotation, review, and source-grounded editing work makes that unlikely.

### Option B: Adopt W3C Web Annotation Directly

**Description:** Persist complete `SpecificResource`, state, and selector JSON-LD.

**Advantages:**

- W3C Recommendation with an established vocabulary
- Existing selector and representation-state semantics
- Interoperability with annotation systems

**Disadvantages:**

- Larger object model than tbd or FlexDoc needs
- JSON-LD/RDF context and vocabulary increase implementation surface
- Does not define the DocRef locator grammar
- Its text normalization leaves application-specific work
- Full annotations conflate targeting with bodies and workflow concerns

The concepts should be reused, but the complete format should not be required.

### Option C: Make a TextRef URI the Data Model

**Description:** Encode document, source validation, and passage into one string.

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

A canonical URI projection should accompany v0.1, but it should remain a reversible
encoding of the normative JSON object rather than the data model itself.
It uses its own scheme or a viewer-owned fragment, never a private fragment imposed on
the referenced document.

### Option D: Make Content Hashes the Primary Identifier

**Description:** Refer to normalized text by digest and treat locations as optional
hints.

**Advantages:**

- Strong content validation
- Straightforward integrity verification
- Deduplication across locations

**Disadvantages:**

- A hash does not say where content can be retrieved
- Current or mutable documents remain important user concepts
- Hash-only references cannot recover a passage in a later version
- Local and internal workflows would need separate locator metadata anyway

An optional source hash belongs beside the DocRef, not in place of it.

### Option E: Prove the TextRef Profile, Then Extract It

**Description:** Define TextRef and its conformance vectors in FlexDoc and a concrete
sidecar consumer, then extract the stable protocol when a TypeScript consumer needs the
same persisted references.

**Advantages:**

- Validates the shape against a real workflow before creating a release surface
- Preserves a path to clean cross-language ownership
- Produces one behavior contract and shared fixtures before implementation duplication
- Reusable by reviews, annotations, citations, edits, and other tools
- Small enough to remain understandable and dependency-free

**Disadvantages:**

- The protocol initially lives in one consumer repository
- Cross-language reuse waits until the second implementation is justified
- Extraction still requires release and compatibility decisions later

This is the recommended approach.

## TextRef Design

### Protocol Types

The public vocabulary should be:

- `DocRef`: requested document locator
- `SpanRef`: passage selector over supplied normalized text
- `TextRef`: whole-document, span, point, or section reference

`source_hash` is an optional field, not a separate public value type.
It validates the canonical source used by a position hint.
The persisted `selector` is a discriminated union; v0.1 defines `type: span` backed by
SpanRef evidence, `type: point` backed by boundary evidence, and `type: section` backed
by heading anchors plus a structure profile. Selector absence represents the complete
document. The public API exposes this as a derived `target_kind` with exactly four
values:

| Target Kind | Wire Shape | Meaning |
| --- | --- | --- |
| `whole_document` | `selector` absent | The complete canonical source |
| `span` | `selector.type: span` | One non-empty arbitrary source range |
| `point` | `selector.type: point` | One zero-width source boundary |
| `section` | `selector.type: section` | One complete parsed heading section |

Whole-document references do not need a redundant `type: document` selector. Point and
section branches likewise do not require standalone PointRef or SectionRef wire types.
SpanRef remains a useful value over supplied text because FlexDoc already exposes it and
section boundary anchors reuse its evidence shape.

`TextRef` is preferable to `DocumentTarget` because it is concise and states the
representation boundary: v0.1 refers to text, not arbitrary binary resources or rendered
layout.

### Persisted Shapes

A whole-document reference has no selector:

```json
{
  "format": "textref/0.1",
  "document": "github:owner/repo@main//docs/design.md",
  "source_hash": "sha256:83f6d4..."
}
```

A passage reference uses a non-empty source quote:

```json
{
  "format": "textref/0.1",
  "document": "github:owner/repo@main//docs/design.md",
  "source_hash": "sha256:83f6d4...",
  "selector": {
    "type": "span",
    "exact": "Canonical source is authoritative.",
    "prefix": "The parser guarantees that ",
    "suffix": " Derived views are secondary.",
    "start": 1842
  }
}
```

A point reference uses context around a zero-width source boundary:

```json
{
  "format": "textref/0.1",
  "document": "github:owner/repo@main//docs/design.md",
  "source_hash": "sha256:83f6d4...",
  "selector": {
    "type": "point",
    "position": 1881,
    "affinity": "before",
    "prefix": "authoritative.",
    "suffix": "\nDerived views"
  }
}
```

A section reference anchors its starting heading and may corroborate the exclusive end
with the next equal-or-higher heading:

```json
{
  "format": "textref/0.1",
  "document": "github:owner/repo@main//docs/design.md",
  "source_hash": "sha256:83f6d4...",
  "selector": {
    "type": "section",
    "syntax": "commonmark",
    "start_anchor": {
      "exact": "## TextRef Design",
      "prefix": "This is the recommended approach.\n\n",
      "suffix": "\n\n### Protocol Types",
      "start": 7421
    },
    "end_anchor": {
      "exact": "## Open Decisions",
      "prefix": "Rendered browser fragments remain a separate adapter concern.\n\n",
      "suffix": "\n\n### Document Location and Portability",
      "start": 12684
    }
  }
}
```

The v0.1 rules are:

- `format` and `document` are required.
- `source_hash` is optional and contains an algorithm-qualified digest of canonical
  source text.
- `selector` is optional.
  Its absence means the whole document.
- A TextRef containing `selector` has no independently recognized Git or URL fragment.
  The final DocRef rules must define this per kind before it is enforced.
- `selector.type` is required.
  v0.1 defines `span`, `point`, and `section`.
- A `span` selector requires an `exact` string containing at least one Unicode code
  point. `prefix` and `suffix` are optional, non-empty immediate context strings.
  `start` is an optional non-negative JSON-safe integer measured in Unicode code points.
  The selected half-open range is `[start, start + code_point_length(exact))`. In-memory
  SpanRef APIs may retain a derived `end`, but the wire format does not store the
  redundant value.
- Span boundaries need not align with Markdown tokens, inline nodes, blocks, headings,
  lines, rendered selections, or parser nodes. They are boundaries in canonical source
  text. A consumer may impose stricter alignment for a particular operation without
  changing TextRef validity.
- A `point` selector requires `affinity: before | after` and normally contains a
  non-negative JSON-safe `position` plus non-empty immediate `prefix` and/or `suffix`
  context. `position` identifies a boundary and can equal the source length.
  It is optional on the wire so a refreshed reference can retain context after a stale
  position is discarded.
  At least one context must remain unless the point is at position zero in empty text
  and is protected by a matching `source_hash`.
- For a point, `prefix` ends immediately before the boundary and `suffix` begins
  immediately after it.
  `before` uses prefix as owning context; `after` uses suffix.
  At document start, use `after`; at document end, use `before`. Empty text is both
  boundaries: either affinity may express insertion behavior, but the point cannot
  recover after a source-hash mismatch because it has no content evidence.
- A `section` selector requires `syntax: commonmark` and `start_anchor` containing the
  same `exact`, `prefix`, `suffix`, and `start` evidence as a SpanRef, without a nested
  `type`. The start anchor selects the complete parsed source span of an ATX or setext
  heading. The section starts at the first code point of that heading and includes its
  nested subsections.
- `end_anchor` is optional and has the same evidence shape. When present, it selects the
  complete heading that begins immediately after the section: the next heading of equal
  or higher level. That heading is excluded from the resolved range. A last section has
  no end anchor because its exclusive end is the end of the document.
- A section constructor should capture `end_anchor` whenever that following heading is
  available. Omitting it is a valid compact form, but loses independent detection of an
  inserted peer heading or other boundary change.
- Section resolution requires a compatible structure adapter. The adapter derives the
  current exclusive end from the parsed heading hierarchy. An end anchor corroborates
  and disambiguates that result but does not replace structural verification. A
  text-only resolver reports `unsupported` instead of treating the reference as a span
  or extending it to the end of the document.
- A mismatch between a resolved end anchor and the derived structural boundary is
  visible `boundary_mismatched` evidence. The resolver must not silently expand or
  contract the section. If only the end heading text changes but the start heading and
  structure remain unambiguous, a consumer may resolve the section while reporting the
  stale end evidence.
- Unknown fields are rejected at every defined schema level.
  Optional non-standard data belongs under an `extensions` object whose keys are
  namespaced by their owner.

The optional fields form four useful profiles:

| Source Hash | Selector | Meaning |
| --- | --- | --- |
| Absent | Absent | Floating reference to the whole document |
| Present | Absent | Verifiable reference to one canonical source value |
| Absent | Present | Span, point, or section that can re-anchor in the resolved document |
| Present | Present | Source-bound target with recovery evidence after edits |

The hash does not make a mutable DocRef retrieve an old version.
A reproducible citation should use an immutable DocRef, such as a Git commit, or
consumer-owned archival provenance.

`selector` is a discriminated union so future selector kinds can be added without
changing the existing branches:

- `table`, `table_row`, or `table_cell` when consumers need structural identity that a
  source span cannot preserve
- Other structural objects such as list items, code blocks, headings without their
  owned section content, or parser-specific nodes
- Discontinuous or multi-span selections
- rendered-text or media selectors with explicit representation semantics

These are extension points, not v0.1 commitments.
Normalized and fuzzy matching do not need new selector kinds because they consume the
same `exact`, context, source hash, and position evidence, including the SpanRef evidence
inside section anchors.

The JSON object is the normative persisted data model and is encoded as UTF-8. YAML is
only a convenience projection: it must use string keys and JSON-compatible values,
reject duplicate keys and custom tags, and deserialize to the same JSON value tree
before schema validation.
YAML-specific scalar types or independent semantics are not part of the protocol.

### URI Projection

The URI projection is a canonical, reversible encoding of one core TextRef.
The proposed v0.1 grammar uses `textref:0.1` followed by a query with these fields:

The URI identifies a target; it does not encode an annotation body, workflow state, or
annotation set. Sharing those records uses an annotation envelope or sidecar that may
contain the URI or its equivalent JSON TextRef.

| Field | Meaning | Applies To |
| --- | --- | --- |
| `doc` | Complete DocRef string | All references |
| `hash` | Algorithm-qualified `source_hash` | Optional |
| `type` | `span`, `point`, or `section` | References with selectors |
| `exact` | Non-empty source quote | Span selector |
| `prefix`, `suffix` | Immediate source context | Span or point selector |
| `start` | Code-point position hint | Span selector |
| `position` | Code-point boundary hint | Point selector |
| `affinity` | `before` or `after` | Point selector |
| `syntax` | `commonmark` | Section selector |
| `start_exact`, `start_prefix`, `start_suffix`, `start_pos` | Start-heading anchor | Section selector |
| `end_exact`, `end_prefix`, `end_suffix`, `end_pos` | Optional exclusive end-heading anchor | Section selector |

Examples:

```text
textref:0.1?doc=.%2Fdesign.md
textref:0.1?doc=.%2Fdesign.md&hash=sha256%3A83f6d4...&type=span&exact=Canonical%20source%20is%20authoritative.&prefix=The%20parser%20guarantees%20that%20&suffix=%20Derived%20views%20are%20secondary.&start=1842
textref:0.1?doc=.%2Fdesign.md&type=point&prefix=authoritative.&suffix=%0ADerived%20views&position=1881&affinity=before
textref:0.1?doc=.%2Fdesign.md&type=section&syntax=commonmark&start_exact=%23%23%20TextRef%20Design&start_pos=7421&end_exact=%23%23%20Open%20Decisions&end_pos=12684
```

Canonical serialization should:

- Map `format: textref/0.1` to the `0.1` path and emit parameters in the table’s order.
  Within a section, emit every `start_*` field before every `end_*` field
- Encode every value as UTF-8 and percent-encode every byte except RFC 3986 unreserved
  characters; encode spaces as `%20`, never `+`
- Emit only fields present in the object and never shorten or normalize their string
  values
- Reject duplicate parameters, empty required values, fields incompatible with the
  selector type, unknown parameters, and unsupported versions
- Refuse core TextRefs containing non-representable extensions rather than silently
  dropping them
- Round-trip through the normative JSON value before structural equality is tested

Two accepted URI strings are canonically equal when parsing and reserializing them
produces the same byte string.
Semantic document equivalence and resolved-target equivalence remain separate questions.

The codec performs no I/O. A custom-scheme handler may resolve the returned TextRef, and
an HTTPS viewer may embed the complete inner URI in its fragment:

```text
https://viewer.example/open#textref:0.1?doc=.%2Fdesign.md&type=span&exact=Canonical%20source
```

The `textref:` scheme remains a specification candidate until registration and
governance are established.
The HTTPS wrapper is deployable sooner because the viewer owns its fragment semantics.
A browser text-fragment URL remains a separate, lossy navigation export for compatible
rendered HTTP resources.

The protocol should define parser and exporter limits rather than assume every channel
accepts arbitrarily long URLs.
Exceeding an export limit is a visible refusal.
Optional compressed, encrypted, or server-backed short links wrap the canonical object
and must declare their codec, confidentiality, and lifetime; they are not alternate
TextRef semantics.

### Compact YAML Annotation Sidecar

A one-document sidecar can remove the largest source of repetition by hoisting
`document` and `source_hash`. Each annotation then stores a bare selector under
`target`, plus its envelope fields:

```yaml
format: text-annotations/0.1
document: ./design.md
source_hash: "sha256:83f6d4..."
annotations:
  - id: A1
    target:
      type: span
      exact: Canonical source is authoritative.
      prefix: "The parser guarantees that "
      suffix: " Derived views are secondary."
      start: 1842
    motivations: [commenting]
    body:
      type: text
      value: Define which normalization profile is canonical.

  - id: A2
    target:
      type: point
      position: 1881
      affinity: before
      prefix: authoritative.
      suffix: "\nDerived views"
    motivations: [commenting]
    body:
      type: text
      value: Add a transition before this sentence.

  - id: A3
    target:
      type: section
      syntax: commonmark
      start_anchor:
        exact: "## TextRef Design"
        prefix: "This is the recommended approach.\n\n"
        suffix: "\n\n### Protocol Types"
        start: 7421
      end_anchor:
        exact: "## Open Decisions"
        prefix: "Rendered browser fragments remain a separate adapter concern.\n\n"
        suffix: "\n\n### Document Location and Portability"
        start: 12684
    motivations: [commenting]
    body:
      type: text
      value: Review the complete design section after internal edits.

  - id: A4
    target: document
    motivations: [commenting]
    body:
      type: text
      value: This note applies to the complete document.
```

`text-annotations/0.1` is a consumer profile around TextRef, not another selector
protocol. A consumer expands each `target` into a complete TextRef using the hoisted
fields before validation or resolution.
The literal `target: document`, as in `A4`, expands to a TextRef without `selector` and
therefore targets the whole document. An object target must be a bare `span`, `point`,
or `section` selector. An omitted target, `null`, `{}`, and an invented
`type: document` are rejected so missing data cannot silently become a whole-document
annotation.
This profile should initially contain exactly one document; a cross-document annotation
uses a complete TextRef or a later explicitly multi-document container.

The YAML rules remain intentionally narrow:

- Parse with YAML 1.2 JSON-compatible scalar semantics and reject duplicate keys,
  aliases, merge keys, custom tags, and non-string mapping keys
- Preserve every string exactly; use quoted or block scalars when YAML could interpret a
  value as another scalar type
- Validate the resulting JSON-compatible value against the container and TextRef schemas
- Treat field order and comments as presentation only
- Permit block scalars for long bodies without giving YAML a second logical model

This shape is concise enough for hand editing and agent generation while remaining
diffable, schema-validatable, and mechanically expandable to normative TextRefs.

### Contextual Annotation View

The standard agent workflow should define a deterministic context renderer without
making its output an interchange format:

```text
context_view = render_context(source, annotation_sidecar, context_lines=2)
```

The renderer resolves the sidecar against `source`, derives one-based line and column
labels, groups overlapping windows, and prints the source and annotation rows described
under
[Contextual Diagnostics Provide the Agent Export Pattern](#contextual-diagnostics-provide-the-agent-export-pattern).
Its options may control context lines, inclusion of resolved workflow items, body
length, color, and event history, but every option must be reported in the header when
it changes visible content.

The default view should contain complete selected source when it is reasonably bounded.
When a configured size budget elides a long selection or body, it must mark the elision,
retain the annotation ID and derived range, and tell the agent that the structured
record contains the complete value.
It must never silently shorten content and then present the result as a round-trippable
annotation.

Because source and annotation changes invalidate the view, consumers regenerate it on
every handoff. Agents return annotation IDs and structured dispositions or edits, not a
modified context-view file.

### Line-Based Construction and Display

Line notation belongs in constructors and resolved results:

- `from_lines(source, first_line, last_line)` accepts one-based inclusive line labels,
  selects from the start of `first_line` to the start of the following line, and creates
  a normal span selector.
  The last selected line includes its terminating LF when one is present.
- `from_line_column(source, line, column, affinity)` creates a point selector at a
  one-based line and code-point column.
- `from_line_boundary(source, line, edge, affinity)` creates a point selector at the
  `start` of a one-based line or at its `end` immediately before the terminating LF. A
  separate end-of-document form handles the boundary after the final line.
- `display_location(source, resolved_range)` returns one-based line and column labels
  whose columns count Unicode code points.

Consumer shorthand such as `design.md:L42-L44` calls these constructors and requires the
source text. It is not a third persisted selector shape.
A consumer may retain the original shorthand as import provenance, but equality and
resolution use the generated TextRef.

Terminal caret alignment is a presentation problem because tabs, combining marks, and
wide characters make code-point columns differ from display cells.
A renderer may compute display-cell columns for underlines, but it must keep the
declared source line/column coordinate separate.

### Canonical Source Profile

The core resolver accepts a Unicode string; byte decoding is an adapter responsibility.
The `textref/0.1` format fixes one canonical source profile:

1. Require Unicode scalar values and reject unpaired surrogates.
2. Convert CRLF and lone CR to LF.
3. Preserve all other code points exactly.
4. Do not normalize Unicode, case, whitespace, BOM, or final newlines.
5. Compute `source_hash` over the normalized string encoded as UTF-8.

In v0.1, a BOM is retained as text, NEL/U+2028/U+2029 are not treated as line endings,
and the presence or absence of a final newline is preserved.
The specification must confirm these compatibility choices before release because each
one affects offsets and hashes.
Byte-oriented adapters must separately define their accepted encodings and decoding
failures.

The digest string includes its algorithm.
RFC 6920 can inform equality, but the field is named `source_hash`, not HTTP
`Content-Digest` or `Repr-Digest`, because its input is an application-normalized source
string. The format version defines the normalization profile, and the digest string
defines the algorithm and value.

### Resolution Semantics

Resolution separates document acquisition from selector resolution:

1. Parse and normalize the DocRef without I/O.
2. Ask a consumer-owned resolver for decoded source text and provenance.
3. Apply the canonical source profile and compute the actual source hash when needed.
4. Compare expected and actual `source_hash`, if one is present.
5. Resolve the selector, if present.
6. Return a typed result containing source-validation status, selection outcome, and
   method.

Recommended exact tiers for a `span` selector:

1. **Source-bound position:** If hashes match and the range derived from `start` equals
   `exact`, accept the position even when the quote occurs elsewhere.
2. **Corroborated position:** Without a matching hash, accept a position only when the
   quote and non-empty captured context corroborate it.
3. **Exact quote search:** Resolve a unique exact occurrence.
4. **Context disambiguation:** Resolve one duplicate only when context uniquely
   identifies it.
5. **Visible failure:** Report missing or ambiguous rather than choosing arbitrarily.

This ladder is exact-v1 behavior.
Case, whitespace, Unicode, or edit-distance relaxation is optional resolver policy and
does not change the persisted reference.

A `point` selector has no quote to verify, so it uses a separate conservative ladder:

1. **Source-bound position:** If hashes match, accept an in-bounds `position`.
2. **Corroborated position:** Without a matching hash, accept `position` only when its
   captured context still meets there.
3. **Two-sided context search:** Find boundaries where `prefix` ends and `suffix`
   begins; resolve only a unique match.
4. **Affinity-owned context:** If an insertion changed the non-owning side, a unique
   prefix can recover `before` affinity or a unique suffix can recover `after` affinity.
   This tier must meet a minimum context-length policy and report the discarded
   corroborating evidence.
5. **Visible failure:** Report missing or ambiguous rather than selecting the nearest
   boundary.

Affinity controls how a point survives an insertion at its boundary; it is not itself
evidence that an otherwise weak match is correct.
If the owning context is deleted or repeated, exact resolution can legitimately orphan
the point. Normalized and fuzzy policies may compare or relax point context in later
stages, using the same thresholds and runner-up margin requirements as span and anchor
matching.

A `section` selector resolves its anchors and structure separately:

1. **Start heading:** Resolve `start_anchor` through the span exact ladder and require
   the structure adapter to identify the matched range as one complete top-level
   CommonMark heading.
2. **Derived boundary:** Derive the exclusive end at the next heading of equal or higher
   level, or at document end.
3. **End corroboration:** If `end_anchor` is present, resolve it and prefer a start
   candidate whose derived boundary equals the end anchor's start. This can disambiguate
   repeated heading text.
4. **Boundary disagreement:** If both anchors resolve but do not describe one parsed
   section, report `boundary_mismatched`; do not silently turn the target into an
   arbitrary source range.
5. **Visible unsupported state:** If the syntax profile or structure adapter is
   unavailable, report `unsupported`; do not treat the start anchor as the complete
   target.

The resolved section range is derived state. Its interior text is not stored as selector
evidence, so edits within that range do not require re-anchoring. A changed heading can
enter the normalized or fuzzy anchor stages under the same policy and confirmation rules
as a span.

### Optional Relaxed Resolution

The resolver API, not the wire format, selects a matching policy:

```text
resolve(ref, text, policy="exact")
resolve(ref, text, policy="normalized")
resolve(ref, text, policy="fuzzy")
```

Each policy includes the preceding policy before adding new stages:

1. `exact` runs only the v0.1 exact ladder.
2. `normalized` may add named transformations such as whitespace collapsing, Unicode
   normalization, or case folding.
   Each transformation is explicit because these equivalences are unsafe for some
   source-editing and multilingual use cases.
3. `fuzzy` first searches within a bounded window around a span or anchor position, then
   may search the whole document using quote similarity, prefix/suffix agreement, and
   proximity.

“Closest” is not a sufficient acceptance rule.
An approximate candidate resolves automatically only when all of the following hold:

- Its algorithm-specific score exceeds an empirically selected absolute threshold.
- Its score exceeds the runner-up by an empirically selected uniqueness margin.
- Available prefix, suffix, position, or structural scope provides enough independent
  corroboration for the consumer’s operation.
- Document-size, quote-size, candidate-count, and work limits have not been exceeded.

Otherwise the result is `missing` or `ambiguous`, with candidates available for review.
Scores are meaningful only with the named method and algorithm version; they are not a
universal confidence scale.
An annotation viewer may display a tentative candidate, while an automated source edit
should require exact resolution or explicit stale-edit approval.

Exact re-anchoring may refresh `start` and `source_hash`. Approximate re-anchoring must
not rewrite quote, boundary context, position, or source validation evidence until a
user or consumer-defined high-assurance process confirms the target.
Literal `exact`, prefix, and suffix remain the persisted evidence even when a normalized
or fuzzy policy derives lowercase, whitespace-normalized, token, or n-gram views for
matching. Those derived views and scores identify a resolver algorithm, not a new
selector fact.

### Edit Robustness Comes From Independent Evidence

No individual field is a permanent anchor:

| Evidence | Role | Expected Failure |
| --- | --- | --- |
| `document` | Finds the current resource | Rename, move, access loss, mutable branch |
| `source_hash` | Validates one coordinate space | Any canonical-text change |
| `start` or `position` | Supplies position and proximity | Insertions, deletions, and reordering |
| `exact` | Supplies primary passage evidence | Edits within the selected text |
| `prefix` and `suffix` | Disambiguate and score context | Nearby edits and moved boilerplate |
| Point `affinity` | Chooses the owning side at an insertion boundary | Deletion or repetition of owning context |
| Section `start_anchor` | Identifies the owning heading without freezing its content | Heading rename, deletion, or duplication |
| Section `end_anchor` | Corroborates the exclusive boundary | Boundary-heading rename or hierarchy change |
| Section structure profile | Derives current owned content | Parser disagreement or heading-level change |
| Future structural scope | Narrows table, cell, or other candidates | Document restructure or dialect change |

Robustness comes from resolving these signals together and degrading visibly when they
disagree. The design does not require a document region, heading path, node identifier,
or version to remain frozen.
Structural paths and identifiers may be optional hints, but they must not override
contradictory quote evidence.

If arbitrary tools edit the selected words or both sides of a point, content-based
recovery becomes probabilistic.
Only retained edit history or CRDT identities can transform anchors through every edit,
and those mechanisms are not portable with a plain text file.
TextRef therefore promises conservative recovery and explicit orphaning, not lossless
survival under all edits.

The result should keep independent axes rather than flattening a stale but successfully
re-anchored reference into one status:

| Axis | Suggested Values |
| --- | --- |
| Document | `resolved`, `unavailable`, `invalid` |
| Source validation | `absent`, `matched`, `mismatched` |
| Selector | `whole_document`, `resolved`, `missing`, `ambiguous`, `boundary_mismatched`, `unsupported` |
| Method | `source_position`, `context_position`, `exact_quote`, `context_quote`, `point_context`, `point_affinity`, `section_structure`, `section_anchors`, `normalized_quote`, `fuzzy_quote`, `none` |

A convenience nullable API may wrap these results, but persisted tools and edit
workflows need the distinctions.
A `resolve_all` API can expose candidates while `resolve_one` preserves conservative
single-target semantics.
Resolving a collection must not suppress candidates merely because another reference
used them: several annotations can intentionally share one target.
Batch optimization may rank joint candidates, but each resolved result must still meet
the single-reference evidence and ambiguity rules independently.

Source-hash mismatch policy depends on the operation:

- A citation or annotation viewer may re-anchor against current content while reporting
  that the source changed.
- A source edit should normally require the expected source hash or explicit stale-edit
  handling.

The protocol should expose the facts and selectable policy, not silently choose one
behavior for every consumer.

### Core and Adapter Boundary

The eventual shared core should provide:

- DocRef parsing, formatting, normalization, validation, and structural equality
- TextRef plus span-, point-, and section-selector validation and serialization
- Canonical TextRef URI parsing and formatting
- Canonical source normalization and hashing
- SpanRef construction from a string and offsets
- Point-selector construction from a source boundary and affinity
- Section-selector construction from heading and optional end-heading SpanRefs
- One-based line-range and line-boundary constructors that materialize source selectors
- Derived one-based line and code-point-column display locations
- Exact span and point resolution over caller-supplied text
- Section resolution through a consumer-supplied CommonMark structure adapter
- Code-point and UTF-16 offset conversion
- Typed resolution results

The core should not provide:

- Filesystem or network access
- GitHub or GitLab authentication
- Redirect, cache, or credential policy
- Markdown rendering
- Contextual annotation, terminal, or agent-prompt rendering
- FlexDoc Node adapters
- Annotation or edit models

Resolvers must separately enforce filesystem roots, allowed schemes and hosts, redirect
limits, response-size limits, timeouts, and credential handling.
Keeping I/O outside the core reduces both dependencies and security exposure.

### Staged Repository and Conformance Layout

The first implementation should keep the specification and fixtures beside FlexDoc’s
consumer profile. When a TypeScript consumer needs the same wire format, extract a
repository such as `textrefs` with this layout:

```text
textrefs/
├── spec/
│   ├── docref.md
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
└── typescript/                 # Added with the second consumer
```

The Markdown specifications are normative.
JSON Schema validates structure.
Shared fixtures define examples and algorithm outcomes.
Neither language implementation is the specification for the other.

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
- Points before and after astral characters and combining sequences
- Points at document start, line start, before LF, document end, and empty text
- Point insertions on both sides of each affinity
- Missing, changed, repeated, and deleted point context
- Heading source ranges and rendered-to-source mapping refusal
- Matching, absent, and stale source hashes
- Exact, normalized, fuzzy, ambiguous, and rejected outcomes
- Approximate best-versus-runner-up margins
- Maximum JSON-safe offsets
- Unknown and duplicate JSON members

### Integration with tbd

tbd should continue owning its current DocRef until the shared profile is proven.
Its eventual integration should:

- Preserve the current DocRef v0.1 spelling where deliberately compatible
- Export and test the public parser, formatter, normalizer, and equality API
- Validate every DocRef-bearing configuration field consistently
- Fix local absolute-path resolution as a consumer issue
- Keep `spec_path` and managed-document `kind + name` identity unchanged
- Add `source_hash` only where source validation or stale-edit protection is needed
- Add TextRef only to fields that actually target passages or points, such as future
  review findings or source citations

Managed-doc caching does not need a SpanRef.
Whole-document features should continue using DocRef or TextRef without `selector`.

### Integration with FlexDoc

FlexDoc should prove the TextRef shape while keeping FlexDoc-specific adapters locally:

- Keep `SpanRef.from_node()` in FlexDoc
- Add `FlexDoc.references(document=...)` as the one document-bound construction,
  resolution, and context surface
- Map paragraphs, sentences, blocks, base blocks, located links, and ordinary nodes to
  span selectors; map sections and section nodes to semantic section selectors
- Add a point-selector constructor and source-span boundary helpers without making
  points pretend to be empty SpanRefs
- Add a section-selector constructor from `Section.heading_block.source_span`, with an
  optional end anchor from the next equal-or-higher heading
- Keep the existing public SpanRef API while testing the new wire projection
- Persist `start` when a TextRef also carries `source_hash`; continue treating unbound
  positions as hints
- Keep `SpanRef.to_text_fragment()` compatible for 0.4 while routing new browser
  navigation work through a rendered-text adapter with explicit refusal rules
- Require document locator and source hash in `DocGraph/v0.2`, making every graph span
  a compact reference basis
- Keep annotations consumer-owned and pass them explicitly to FlexDoc for rendering or
  graph serialization rather than storing them as mutable `FlexDoc` state
- Use one `DocGraph` runtime model and builder; annotations optionally populate the same
  `DocGraph/v0.2` wire contract
- Use bare `span`, `point`, or `section` selectors for annotations embedded in a
  DocGraph whose enclosing source already supplies document and source-hash context
- Use complete TextRef for annotations detached from a graph or targeting another
  document
- Map annotations on a parsed node to its full `source_span`; map a complete heading
  section to a section selector; require an explicit adapter when a selection originates
  from rendered text instead

The protocol decision should precede Phase 2 work on annotation ownership, batch
resolution, and source-validated suggested edits.
Rendered browser fragments remain a separate FlexDoc adapter concern.

## Open Decisions

### Document Location and Portability

1. **Application syntax or URI:** Should `github:` and `gitlab:` remain explicitly
   application-defined DocRef forms, or should Git locations become structured objects?
   They are not registered URI schemes.
2. **Portable profile:** Should portable persisted TextRefs reject `internal:` and local
   DocRefs, or permit them with an explicit resolver namespace/base?
3. **Git hosts:** Should v0.1 remain GitHub/GitLab-specific or define a generic host
   form without overgeneralizing forge behavior?
4. **Fragment migration:** Should existing DocRef fragments remain opaque, be split into
   a presentation field, or be rejected only when `selector` is present?
5. **Equality:** The protocol needs separate names for structural DocRef equality,
   matching source hashes, and two locators resolving to the same target.

### Source Validation and Canonical Text

6. **Digest representation:** Use `sha256:<hex>`, RFC 6920 encoding, or an extensible
   algorithm/value object?
7. **Normalization edge cases:** Confirm the proposed preservation of BOM, final
   newline, NEL, and Unicode line separators, and define which byte-decoding profiles
   adapters may claim.
8. **Raw bytes:** Does a later profile need a raw-byte digest in addition to normalized
   `source_hash` for archival provenance?
9. **Authentication:** Document clearly that a digest detects mismatch but does not
   establish who authored or supplied the reference.

### Span Construction and Resolution

10. **Point construction policy:** What minimum owning-context length is safe for
    one-sided recovery, and when may an empty-document point rely only on a source hash?
11. **Context policy:** Is context length a normative construction rule or caller
    policy? A shared default is convenient, but hard-coding 24 characters into the wire
    contract is unnecessary.
12. **Context semantics:** Should stale context be advisory when `exact` is unique, as
    FlexDoc behaves today, or a strict constraint whenever supplied?
13. **Grapheme boundaries:** Should validation reject spans that split a grapheme
    cluster, warn, or document a justified deviation from the Web Annotation model’s
    normative SHOULD NOT?
14. **Approximate matching:** Which named normalization stages, algorithms, thresholds,
    and uniqueness margins survive evaluation against the edited-document corpus?
15. **Immutability:** Should resolution return an updated immutable SpanRef rather than
    mutate positions in place?
16. **Discontinuous selections:** Are multiple spans one TextRef collection, an
    annotation concern, or a future selector type?
17. **Batch ambiguity:** Should a batch resolver ever use global assignment constraints,
    or must every selector resolve independently so iteration order and assumptions
    about target uniqueness cannot manufacture certainty?

### Section Construction and Resolution

18. **Structure profile:** Is `syntax: commonmark` sufficiently precise for ATX and
    setext heading sections across implementations, or does the format need a named
    parser/conformance profile?
19. **End-anchor policy:** Should the recommended default to capture `end_anchor`
    whenever a following equal-or-higher heading exists become a normative requirement
    for full-profile exporters? Define whether missing end evidence is advisory and
    whether a resolved disagreement always produces `boundary_mismatched`.
20. **Section granularity:** Does v0.1 need only a complete section including nested
    subsections, or also the heading alone and direct content excluding subsections?
    The latter two are currently ordinary spans.

### Annotation Sidecar Composition

21. **Orphan representation:** Should the resolution result define a persistable
    orphaned state and a confidence score for approximate methods, so independent
    sidecar tools share failure semantics instead of inventing their own?
22. **Web Annotation mapping:** Should the specification include a normative directional
    mapping from sidecar annotations to W3C Web Annotation JSON so anchors can move
    between sidecars and annotation stores despite their different ambiguity behavior?
23. **Annotation profile ownership:** Should FlexDoc publish the proposed small
    `text-annotation/0.1` envelope, or only examples showing consumers how to compose
    TextRef with W3C/EPUB-compatible motivations, bodies, styles, and provenance?
24. **Captured display text:** What limits and normalization apply when `captured_text`
    intentionally differs from a source-grounded span or section-anchor quote?
25. **Container synchronization:** Should an annotation sidecar standardize generations,
    tombstones, and deletion timestamps, or leave those to live-sync and autosave
    containers as Plannotator does?

Sidecar hoisting is a consumer composition rule: a sidecar may supply shared `document`
and `source_hash` context at the container level for bare `span`, `point`, or `section`
selectors without changing the protocol’s standalone TextRef shape.
Because the shared hash binds every retained position, consumers must update all
positions or drop stale positions before changing the hoisted hash.

### Edits, Diffs, and Redlines

26. **Edit body schema:** Should the first editing profile define explicit `insert`,
    `delete`, and `replace` variants, or derive the operation from target type and the
    presence of replacement content?
27. **Application precondition:** Must every automatically applicable edit carry a
    matching `source_hash`, or can an immutable DocRef plus exact target evidence
    satisfy the same requirement?
28. **Stale proposals:** Which user confirmation or consumer-defined validation permits
    a relocated edit to apply after its base hash differs?
29. **Change-set semantics:** Which consumer first needs portable atomic groups, and
    what ordering, overlap, co-located insertion, cross-file, and rollback rules does it
    require?
30. **Projection guarantees:** Which metadata and operations must survive directional
    Git patch, CriticMarkup, GLFM, HTML, Pandoc, SARIF, and review-suggestion adapters?

### Export and Context Projections

31. **URI deployment:** Should `textref:` ship only after provisional IANA registration,
    and which application or organization owns its stable specification and change
    control? Which HTTPS viewer base supplies universally clickable links before then?
32. **URI limits:** What minimum input size must conforming parsers accept, when must an
    exporter refuse, and which extensions or future selector fields require a new URI
    version rather than additional parameters?
33. **Sidecar ownership:** Should FlexDoc publish `text-annotations/0.1` as a concrete
    one-document YAML profile, including its body and workflow vocabulary, or should a
    separate annotation consumer own it?
34. **Context-view contract:** Which defaults for context lines, size budgets, resolved
    workflow states, elision markers, and unresolved sections produce stable agent
    handoffs without encouraging consumers to parse the display output?
35. **Line shorthand:** Which one-based forms cover whole lines, line ranges, columns,
    and line boundaries without colliding with Windows paths or DocRef syntax?

### Safety, Privacy, and Evolution

36. **Quote limits:** What maximum `exact`, `captured_text`, prefix, suffix, document
    size, and candidate count prevent denial of service and accidental copying of large
    copyrighted or sensitive passages?
37. **Versioning:** What changes are compatible within `textref/0.x`, and when does a
    new major become necessary?
38. **Governance:** Who owns releases and adjudicates behavior changes when tbd and
    FlexDoc need different policies?
39. **Extraction compatibility:** When the second-language implementation is justified,
    does FlexDoc preserve its current import/module identity or take an intentional
    pre-1.0 breaking change?

These questions should be resolved in the protocol specification or explicit adoption
profiles. They should not be left to diverging implementation defaults.

## Recommendations

1. Prove TextRef through FlexDoc and a YAML sidecar consumer before extracting a
   standalone repository.
2. Define one language-neutral specification and conformance corpus.
3. Model TextRef as `document + optional source_hash + optional typed selector`, with
   the exhaustive target kinds `whole_document`, `span`, `point`, and `section`.
   Keep selector absence as the compact whole-document wire representation.
4. Keep DocRef as the locator, `source_hash` as an optional strong validator, and
   SpanRef as quote/context/position evidence over arbitrary non-empty source ranges.
   Do not require Markdown-node alignment for basic span validity.
5. Include a distinct `point` selector with boundary context and before/after affinity;
   do not encode points as empty quotes or one-character spans.
6. Include a `section` selector with a CommonMark structure profile, a required
   start-heading SpanRef anchor, and an optional exclusive end-heading anchor. Derive
   the current range from parsed heading structure rather than freezing section text.
7. Represent table, row, cell, header-cell, heading-only, and other Markdown-node
   annotations as source spans in v0.1. Add structural selector kinds only when a
   consumer demonstrates identity requirements that spans cannot meet.
8. Use structured JSON as the normative data model, with a restricted YAML projection
   and a canonical, reversible TextRef URI projection.
9. Restrict v0.1 to normalized Unicode source text.
10. Keep all I/O, Markdown structure parsing, and rendering in consumer-owned adapters.
11. Keep annotation bodies, motivations, styles, tags, publication metadata, and provider
   locations in a small consumer envelope rather than TextRef.
12. Use a span's `selector.exact` and a section anchor's `exact` as retained source
    quotes; add `captured_text` only when the user-visible or imported text differs from
    that source representation.
13. Give annotations their own IDs and allow several annotations to share a target; do
    not key persisted comments by an element index, line range, or serialized TextRef.
14. Make source-validation, ambiguity, boundary disagreement, unsupported structure,
    method, and orphan outcomes visible.
15. Keep exact-v1 behavior stable while adding normalized and fuzzy resolver policies
    without changing persisted references.
16. Require thresholds, runner-up margins, and independent corroboration before an
    approximate candidate resolves automatically.
17. Never rewrite persisted evidence after approximate matching without confirmation.
18. Resolve each selector conservatively on its own evidence.
    A batch API may expose or rank joint candidates, but iteration order, `used` sets,
    and assumed target uniqueness must not convert ambiguity into a match.
19. Validate the sidecar profile against MRSF, W3C Web Annotation, EPUB Annotations,
    EPUB CFI recovery, Readwise imports, Plannotator share/draft/API projections, and an
    edited-document corpus before publishing v0.1; include Markdown Review whole-block
    comments, embedded questions, HiNote in-band highlight fixtures, and a directional
    Remark review export.
20. Keep the logical JSON format structured and versioned.
    Treat contextual Markdown, compressed URLs, encrypted links, and server-backed short
    links as optional projections around the canonical object or URI.
21. Keep autosave generations, tombstones, and live event sequencing in the annotation
    container rather than TextRef.
22. Keep annotation workflow status independent from document, source-validation, and
    selector-resolution outcomes.
    An unresolved annotation may be anchored, relocated, or orphaned.
23. Let an annotation container retain a last-known target, confirmed target revisions,
    and actor-attributed events.
    These are history around TextRef, not additional fields inside TextRef.
24. Require a concrete edit or explicit human decision before an agent marks review work
    complete; source-hash mismatch, re-anchoring, and orphaning are not completion.
25. Keep diff, redline, and edit-operation semantics out of TextRef.
    A TextRef identifies the source target regardless of how a consumer presents or
    changes it.
26. Use Git/source diffs as the primary artifact for reviewing and applying Markdown
    changes. Treat rendered and syntax-tree diffs as derived review views.
27. Add a discriminated `editing` body in an annotation profile for insert, delete, and
    replace proposals; use point selectors for insertions and span selectors for
    deletions and replacements.
28. Require a matching base source hash before automatic edit application.
    A relocated stale proposal remains reviewable but requires confirmation or
    regeneration.
29. Define directional adapters for Git patches, CriticMarkup, GLFM inline diffs, raw
    `<ins>/<del>`, Pandoc tracked-change spans, SARIF fixes, and platform suggestions.
    Standardize a separate atomic change-set format only when a concrete consumer needs
    its ordering, overlap, and rollback semantics.
30. Define the readable `textref:0.1?...` codec beside the JSON schema, with canonical
    parameter order, UTF-8 percent encoding, strict parsing, round-trip fixtures, size
    limits, and visible refusal.
    Do not append it to the target document’s fragment.
31. Use an application-controlled HTTPS fragment wrapper for clickable links until the
    `textref` scheme has stable governance and provisional registration.
    Keep browser text fragments and GitHub line permalinks as separate directional
    navigation exports.
32. Publish a concise one-document YAML sidecar profile that hoists `document` and
    `source_hash`, retains bare span, point, and section selectors, treats omitted
    targets as invalid, uses literal `target: document` for whole-document references,
    and expands mechanically to complete TextRefs before validation.
33. Standardize a non-normative ASCII context view for agent handoff: merged
    line-numbered excerpts, adjacent ID-tagged annotation rows, explicit point affinity,
    section boundaries, source and resolution status, and a separate unresolved section.
34. Encourage one-based line and column notation for user and agent input and display,
    but materialize it immediately into quote/context/position TextRefs.
    Never persist a line range as the only mutable-document anchor.

## Next Steps

- [ ] Resolve the decisions listed under [Open Decisions](#open-decisions)
- [ ] Prototype normative TextRef JSON plus canonical URI parsing and formatting, with
  cross-language round-trip, ordering, percent-encoding, invalid-input, and size-limit
  fixtures
- [ ] Prototype the four target kinds: selector-free whole document, arbitrary source
  span, boundary point, and CommonMark section with start and optional end anchors
- [ ] Add section fixtures for ATX and setext headings, nested subsections, repeated and
  renamed headings, end-of-document sections, moved boundaries, missing adapters, and
  explicit end-anchor disagreement
- [ ] Prototype the one-document YAML annotation sidecar with hoisted `document` and
  `source_hash`, bare span/point/section selectors, literal whole-document targets, and
  mechanical expansion to complete TextRefs
- [ ] Prototype one-based `from_lines`, `from_line_column`, `from_line_boundary`, and
  `display_location` helpers without adding a persisted line-selector branch
- [ ] Add arbitrary-span fixtures that begin and end inside inline syntax, cross block
  and node boundaries, select full nodes, and exercise the grapheme-boundary decision
- [ ] Prototype the small annotation envelope for highlights, notes, bookmarks, styles,
  tags, `captured_text`, and import provenance
- [ ] Prototype a typed edit-annotation profile for insert, delete, and replace bodies,
  including strict base-hash application and stale-proposal confirmation
- [ ] Build directional diff/redline fixtures for Git patches, GFM strikethrough, GLFM
  inline diff, raw `<ins>/<del>`, CriticMarkup, Pandoc tracked-change spans, SARIF
  fixes, and GitHub/GitLab suggestions
- [ ] Compare line, word, rendered, and Markdown-tree diff views on reflowed prose,
  links, emphasis, lists, tables, metadata, and code fences
- [ ] Test table annotations as source spans over phrases, complete cells, header cells,
  rows, and tables, including escaped pipes and inline markup; record the first use case
  that cannot preserve required identity without a structural table selector
- [ ] Evaluate `*.md diff=markdown` and an appropriate Markdown word-diff policy for the
  repository without changing patch or merge semantics
- [ ] Defer an atomic `TextChangeSet` schema until a consumer supplies concrete overlap,
  ordering, cross-file, rollback, and result-validation requirements
- [ ] Write the normative TextRef/DocRef/SpanRef specifications and JSON Schemas,
  including the section-selector structure-adapter contract
- [ ] Specify point-selector construction, affinity, exact recovery, and conformance
  vectors
- [ ] Build shared exact-resolution and edited-document fixtures
- [ ] Evaluate normalized and fuzzy thresholds against false attachment, ambiguity,
  orphan, and recovery rates
- [ ] Integrate FlexDoc before its annotation and suggested-edit schema work
- [ ] Compare the sidecar against MRSF and directional Web/EPUB Annotation mappings
- [ ] Build a directional Plannotator adapter that maps `originalText` to
  `captured_text` or a rendered-text selector without treating its DOM metadata as a
  source anchor
- [ ] Build a Markdown Review adapter fixture that maps whole parsed blocks to source
  selectors, general notes to whole-document targets, and embedded questions to typed
  response bodies without persisting element indices
- [ ] Build HiNote adapter fixtures for `==...==`, `<mark>`, `<span>`, repeated text,
  UTF-16/code-point conversion, structural block hints, virtual file comments, and
  arbitrary color extensions
- [ ] Define a directional Remark adapter fixture for independent workflow and anchor
  states, UTF-16 conversion, active and last-known anchors, matcher provenance, and
  optional history without assuming undocumented hash or line semantics
- [ ] Prototype an agent review loop that lists actionable annotations, returns
  ambiguous work for clarification, updates status only after edits, rechecks the queue,
  and produces a final structured export
- [ ] Define and golden-test the non-normative ASCII context view from canonical sidecar
  JSON: verified line labels, merged context windows, source quotes, point affinity,
  edit bodies, explicit elision, and unresolved sections
- [ ] Test custom-scheme links, HTTPS fragment wrappers, browser text fragments, RFC
  7763 line fragments, and GitHub commit line permalinks as distinct export profiles
- [ ] Test Kindle and Readwise imports without treating provider locations as source
  offsets or publication metadata as edition proof
- [ ] Extract a standalone package and TypeScript mirror only when a concrete second
  consumer needs the persisted format
- [ ] Add rendered-text adapters only after source-text v0.1 is stable

## Evidence Base and Limitations

The evidence base includes:

- tbd v0.3.0 managed DocRef and docmap documentation
- The installed tbd TypeScript bundles for parsing, caching, fork manifests, and public
  exports
- FlexDoc’s SpanRef, DocGraph source metadata, tests, design specification, and active
  roadmap
- Existing project research on stable span references, document models, and multilayer
  parsing
- Primary W3C, WICG, IETF, IANA, ECMAScript, Package URL, and Software Heritage sources
- EPUB CFI recovery assertions and extension semantics, HTTP strong validators, Memento
  historical-version retrieval, and GNU `patch` context relaxation
- Git patch and word-diff behavior, Git’s built-in Markdown diff driver, GitHub rendered
  prose diffs, immutable line permalinks, review-comment diff locations, and
  suggestions, plus GitLab inline diffs and suggestions
- RFC 5147 plain-text character and line fragments, RFC 7763 Markdown line fragments,
  SARIF regions and context regions, rustc structured and rendered diagnostics, and
  reviewdog’s compact and structured diagnostic inputs
- CommonMark heading structure, GFM tables and strikethrough, HTML `ins`/`del`,
  CriticMarkup through MultiMarkdown, Pandoc tracked-change spans, Lowdown’s
  Markdown-tree diff, Web Annotation RangeSelector and `editing` motivation, and SARIF
  structured fixes
- The 2026 EPUB Annotations draft, its use cases and vocabulary, the Web Annotation
  model, and DOM collapsed-range boundary semantics
- Official Readwise API and Reader documentation for highlight text, notes, colors,
  tags, locations, timestamps, imports, and low-confidence matching behavior
- Official Amazon documentation for the user-visible Kindle notes/highlights sync use
  case; no stable public Kindle interchange schema is available
- Plannotator `v0.23.1` source at commit `29513e19`, including plan, HTML, and code
  anchors; share payloads; draft JSON; external annotation events; feedback export; and
  archive storage
- Markdown Review source at commit `149fe77`, including element extraction, rendered
  block targeting, in-memory review state, embedded question parsing, Markdown feedback
  generation, CLI JSON wrapping, VS Code document refresh, and checked-in feedback
  snapshots
- HiNote `0.5.7` source at commit `49f6753`, including its version 2.0 sidecar JSON,
  highlight and comment types, regex extraction, contextual and fuzzy match cascade,
  anchor refresh, orphan cleanup, virtual file comments, Obsidian block references, and
  Markdown export
- Remark’s February 2026 Reddit launch description, product and privacy pages, public
  Homebrew cask at commit `ebb3abd`, `2026.4.0` update feed, bundled installable agent
  skill and MCP reference, observable CLI JSON keys, and static metadata from the
  checksum-verified signed distribution; the evidence excludes application source code
  and user data
- WICG and WHATWG specifications, MDN, caniuse, and browser release notes for
  text-fragment mechanics and support
- Annotation-system prior art: the Hypothesis client source and blog, the W3C Web
  Annotation Recommendations, MRSF, standoff formats (brat, STAM, WebAnno), CRDT
  anchoring designs (Peritext, Yjs, Automerge), and the annotation-positioning
  literature (Phelps and Wilensky 2000; Brush et al.
  2001)

The conclusions do not include an implementation spike or performance benchmark.
Context-size, fuzzy-matching, and large-document limits therefore still require
empirical validation.
Diff/redline adapter round trips, stale-edit application safety, and multi-edit overlap
semantics also require fixtures and implementation tests.
The proposed TextRef URI codec, YAML container profile, line constructors, and
contextual agent view have no implementation spike or cross-tool usability measurement;
URL size limits and context-budget defaults remain open decisions.
The section selector also lacks cross-parser conformance fixtures, and the span-only
table approach has not yet been tested against rendered cell selection or structural
edits.

## References

- [tbd DocRef format](https://github.com/jlevy/tbd/blob/main/packages/tbd/docs/references/docref-format.md)
- [tbd docmap format](https://github.com/jlevy/tbd/blob/main/packages/tbd/docs/references/docmap-format.md)
- [FlexDoc stable span-reference research](research-2026-05-30-span-references.md)
- [FlexDoc source-grounded document-model research](research-2026-05-29-document-model.md)
- [FlexDoc multilayer parsing research](research-2026-05-30-multilayer-parsing.md)
- [FlexDoc design specification](../../flexdoc-spec.md)
- [FlexDoc stabilization roadmap](../specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md)
- [W3C Web Annotation Data Model](https://www.w3.org/TR/annotation-model/)
- [W3C Selectors and States](https://www.w3.org/TR/selectors-states/)
- [W3C Character Model: String Matching](https://www.w3.org/TR/charmod-norm/#sec-Matching)
- [EPUB Annotations 1.0](https://www.w3.org/TR/epub-anno-10/)
- [EPUB Annotations Use Cases and Requirements](https://www.w3.org/TR/epub-anno-ucr/)
- [Digital Publishing Annotation Use Cases](https://www.w3.org/TR/dpub-annotation-uc/)
- [EPUB Annotations Vocabulary 1.0](https://www.w3.org/TR/epub-anno-vocab-10/)
- [EPUB Canonical Fragment Identifiers 1.1](https://w3c.github.io/epub-specs/epub33/epubcfi/)
- [DOM Standard: ranges](https://dom.spec.whatwg.org/#ranges)
- [URL Fragment Text Directives](https://wicg.github.io/scroll-to-text-fragment/)
- [MDN: Text fragments](https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Fragment/Text_fragments)
- [Chrome: Share or link to quotes and text](https://support.google.com/chrome/answer/10256233)
- [Firefox 131 release notes](https://developer.mozilla.org/en-US/docs/Mozilla/Firefox/Releases/131)
- [Firefox 145 release notes](https://www.firefox.com/en-US/firefox/145.0/releasenotes/)
- [WebKit: Safari 16.1 text-fragment support](https://webkit.org/blog/13399/webkit-features-in-safari-16-1/)
- [WebKit: Safari 18.2 text-fragment link creation](https://webkit.org/blog/16301/webkit-features-in-safari-18-2/)
- [WebKit bug 273466: `document.fragmentDirective`](https://bugs.webkit.org/show_bug.cgi?id=273466)
- [whatwg/html #11895: upstreaming text fragments](https://github.com/whatwg/html/pull/11895)
- [web.dev: Text fragments](https://web.dev/articles/text-fragments)
- [caniuse: URL scroll-to-text fragment](https://caniuse.com/url-scroll-to-text-fragment)
- [WICG fragment-directive API explainer](https://github.com/WICG/scroll-to-text-fragment/blob/main/fragment-directive-api.md)
- [WICG selector() directive proposal](https://github.com/WICG/scroll-to-text-fragment/blob/main/EXTENSIONS.md)
- [text-fragments-polyfill](https://github.com/GoogleChromeLabs/text-fragments-polyfill)
- [Chromium text-fragment selector generator](https://chromium.googlesource.com/chromium/src/+/main/third_party/blink/renderer/core/fragment_directive/text_fragment_selector_generator.cc)
- [CSS Pseudo-Elements Level 4: ::target-text](https://drafts.csswg.org/css-pseudo-4/#selectordef-target-text)
- [RFC 3986: URI Generic Syntax](https://www.rfc-editor.org/rfc/rfc3986.html)
- [RFC 5147: `text/plain` Fragment Identifiers](https://www.rfc-editor.org/rfc/rfc5147.html)
- [RFC 6920: Naming Things with Hashes](https://www.rfc-editor.org/rfc/rfc6920.html)
- [RFC 7089: Memento](https://www.rfc-editor.org/rfc/rfc7089.html)
- [RFC 7493: I-JSON](https://www.rfc-editor.org/rfc/rfc7493.html)
- [RFC 7595: URI Scheme Guidelines](https://www.rfc-editor.org/rfc/rfc7595.html)
- [IANA URI Scheme Registry](https://www.iana.org/assignments/uri-schemes/uri-schemes.xhtml)
- [RFC 7763: The `text/markdown` Media Type](https://www.rfc-editor.org/rfc/rfc7763.html)
- [RFC 8259: JSON](https://www.rfc-editor.org/rfc/rfc8259.html)
- [RFC 8820: URI Design and Ownership](https://www.rfc-editor.org/rfc/rfc8820.html)
- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
- [RFC 9530: Digest Fields](https://www.rfc-editor.org/rfc/rfc9530.html)
- [ECMAScript String Type](https://tc39.es/ecma262/#sec-ecmascript-language-types-string-type)
- [Package URL specification (ECMA-427)](https://ecma-international.org/publications-and-standards/standards/ecma-427/)
- [SWHID specification (ISO/IEC 18670:2025)](https://www.swhid.org/)
- [Hypothesis: fuzzy anchoring](https://web.hypothes.is/blog/fuzzy-anchoring/)
- [Hypothesis client quote matching](https://github.com/hypothesis/client/blob/main/src/annotator/anchoring/match-quote.ts)
- [Quantifying Orphaned Annotations in Hypothes.is](https://arxiv.org/abs/1512.06195)
- [approx-string-match](https://github.com/robertknight/approx-string-match-js)
- [diff-match-patch (archived 2024)](https://github.com/google/diff-match-patch)
- [GNU `patch`: Helping `patch` Find Inexact Matches](https://www.gnu.org/software/diffutils/manual/html_node/Inexact.html)
- [Git patch format](https://git-scm.com/docs/diff-generate-patch.html)
- [Git word diff](https://git-scm.com/docs/git-diff)
- [Git Markdown diff attributes](https://git-scm.com/docs/gitattributes)
- [GitHub prose diffs](https://docs.github.com/en/repositories/working-with-files/using-files/working-with-non-code-files)
- [GitHub permanent line links](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-a-permanent-link-to-a-code-snippet)
- [GitHub pull-request review comments API](https://docs.github.com/en/rest/pulls/comments)
- [GitHub suggested changes](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/incorporating-feedback-in-your-pull-request)
- [GitLab Flavored Markdown inline diff](https://docs.gitlab.com/user/markdown/#inline-diff)
- [GitLab suggested changes](https://docs.gitlab.com/user/project/merge_requests/reviews/suggestions/)
- [CommonMark raw HTML](https://spec.commonmark.org/0.31.2/#raw-html)
- [CommonMark fenced code blocks](https://spec.commonmark.org/0.31.2/#fenced-code-blocks)
- [CommonMark ATX and setext headings](https://spec.commonmark.org/0.31.2/#atx-headings)
- [GFM strikethrough](https://github.github.com/gfm/#strikethrough-extension-)
- [GFM tables](https://github.github.com/gfm/#tables-extension-)
- [GitHub fenced code blocks](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-and-highlighting-code-blocks)
- [HTML insertion and deletion elements](https://html.spec.whatwg.org/dev/edits.html)
- [MultiMarkdown CriticMarkup](https://fletcher.github.io/MultiMarkdown-6/MMD_Users_Guide.html#criticmarkup)
- [Pandoc tracked changes](https://pandoc.org/demo/example2.html#option--track-changes)
- [Lowdown Markdown diff engine](https://kristaps.bsd.lv/lowdown/diff.html)
- [W3C Web Annotation `editing` motivation](https://www.w3.org/TR/annotation-vocab/#editing)
- [Apache Annotator (retired 2025)](https://github.com/apache/incubator-annotator)
- [Plannotator repository](https://github.com/backnotprop/plannotator)
- [Plannotator `v0.23.1` source](https://github.com/backnotprop/plannotator/tree/29513e1984805a582e644b192b82a8d9cec31943)
- [Plannotator annotation types](https://github.com/backnotprop/plannotator/blob/29513e1984805a582e644b192b82a8d9cec31943/packages/ui/types.ts)
- [Plannotator sharing format](https://github.com/backnotprop/plannotator/blob/29513e1984805a582e644b192b82a8d9cec31943/packages/ui/utils/sharing.ts)
- [Plannotator draft storage](https://github.com/backnotprop/plannotator/blob/29513e1984805a582e644b192b82a8d9cec31943/packages/shared/draft.ts)
- [Plannotator external annotation protocol](https://github.com/backnotprop/plannotator/blob/29513e1984805a582e644b192b82a8d9cec31943/packages/core/external-annotation.ts)
- [Markdown Review repository](https://github.com/rwoll/markdown-review)
- [Markdown Review source](https://github.com/rwoll/markdown-review/tree/149fe77c44645d16db4ba9689bde4952056404a6)
- [Markdown Review element extraction](https://github.com/rwoll/markdown-review/blob/149fe77c44645d16db4ba9689bde4952056404a6/packages/core/src/extract-elements.ts)
- [Markdown Review review state](https://github.com/rwoll/markdown-review/blob/149fe77c44645d16db4ba9689bde4952056404a6/packages/core/src/state.ts)
- [Markdown Review feedback projection](https://github.com/rwoll/markdown-review/blob/149fe77c44645d16db4ba9689bde4952056404a6/packages/core/src/components/NotesPanel.tsx)
- [Markdown Review CLI transport](https://github.com/rwoll/markdown-review/blob/149fe77c44645d16db4ba9689bde4952056404a6/packages/markdown-review/src/cli.ts)
- [Markdown Review feedback snapshot](https://github.com/rwoll/markdown-review/blob/149fe77c44645d16db4ba9689bde4952056404a6/tests/__snapshots__/feedback-output.spec.ts/feedback-inline-annotation.txt)
- [HiNote repository](https://github.com/CatMuse/HiNote)
- [HiNote `0.5.7` source](https://github.com/CatMuse/HiNote/tree/49f6753725e2af9763fd50ff2633b18be9bcc5b0)
- [HiNote persisted highlight format](https://github.com/CatMuse/HiNote/blob/49f6753725e2af9763fd50ff2633b18be9bcc5b0/src/storage/HighlightDataFormat.ts)
- [HiNote highlight extraction and context capture](https://github.com/CatMuse/HiNote/blob/49f6753725e2af9763fd50ff2633b18be9bcc5b0/src/services/highlight/HighlightExtractor.ts)
- [HiNote matching cascade](https://github.com/CatMuse/HiNote/blob/49f6753725e2af9763fd50ff2633b18be9bcc5b0/src/services/highlight/HighlightMatchStrategies.ts)
- [HiNote anchor refresh](https://github.com/CatMuse/HiNote/blob/49f6753725e2af9763fd50ff2633b18be9bcc5b0/src/services/highlight/HighlightMatcher.ts)
- [HiNote orphan handling](https://github.com/CatMuse/HiNote/blob/49f6753725e2af9763fd50ff2633b18be9bcc5b0/src/services/HighlightManager.ts)
- [HiNote Markdown export](https://github.com/CatMuse/HiNote/blob/49f6753725e2af9763fd50ff2633b18be9bcc5b0/src/services/export/ExportContentRenderer.ts)
- [Remark Reddit launch post](https://www.reddit.com/r/ClaudeAI/comments/1rdfag6/i_built_a_markdown_annotation_tool_that/)
- [Remark product and workflow](https://getremark.app/)
- [Remark privacy and local-storage statement](https://getremark.app/privacy/)
- [Remark public Homebrew cask](https://github.com/mfreiwald/homebrew-tap/blob/ebb3abd54f499e5dc6383d1e478b80b277fcef2b/Casks/remark.rb)
- [Remark `2026.4.0` update feed](https://updates.getremark.app/stable/appcast.xml)
- [Remark `2026.4.0` signed distribution](https://updates.getremark.app/stable/2026.4.0/Remark.dmg)
- [Readwise API](https://readwise.io/api_deets)
- [Readwise Reader: highlights, tags, and notes](https://docs.readwise.io/reader/docs/faqs/highlights-tags-notes)
- [Amazon: Sync Your Kindle Reading Progress Across Devices](https://digprjsurvey.amazon.com/csad/help/node/GDCAMDFMC2LZP6BR)
- [Phelps and Wilensky: Robust Locations for Annotation](https://www.dlib.org/dlib/july00/wilensky/07wilensky.html)
- [Brush et al.: Robust Annotation Positioning in Digital Documents](https://dl.acm.org/doi/10.1145/365024.365117)
- [Brush and Bargeron: Robustly Anchoring Annotations Using Keywords](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr-2001-107.pdf)
- [brat standoff annotation format](https://brat.nlplab.org/standoff.html)
- [STAM: Stand-off Text Annotation Model](https://annotation.github.io/stam/)
- [SARIF v2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
- [rustc JSON diagnostics](https://doc.rust-lang.org/beta/rustc/json.html)
- [reviewdog diagnostic and diff formats](https://github.com/reviewdog/reviewdog)
- [MRSF: Markdown Review Sidecar Format](https://github.com/wictorwilen/MRSF)
- [iA Markdown Annotations](https://github.com/iainc/Markdown-Annotations)
- [CriticMarkup](https://github.com/CriticMarkup/CriticMarkup-toolkit)
- [Semiont selector protocol](https://github.com/The-AI-Alliance/semiont/blob/main/docs/protocol/W3C-SELECTORS.md)
- [Codetations: persistent out-of-document notes](https://arxiv.org/abs/2504.18702)
- [Peritext: a CRDT for rich-text collaboration](https://www.inkandswitch.com/peritext/)
- [Google Drive API: manage comments and replies](https://developers.google.com/workspace/drive/api/guides/manage-comments)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
