# Research: A Portable DocRef, SpanRef, and TextRef Microformat

**Date:** 2026-07-10 (last updated 2026-07-12)

**Author:** Codex, synthesizing existing FlexDoc and tbd design work

**Status:** Complete (proposal for review)

## Overview

tbd and FlexDoc each solve one half of the same reference problem:

- tbd’s **DocRef** locates a document and records where it came from
- FlexDoc’s **SpanRef** identifies a passage within source text and can recover that
  passage after offsets move

Neither type alone is a portable reference to a passage.
A DocRef does not identify an exact representation or select text.
A SpanRef assumes the caller already has the correct source text.
Cross-repository reviews, durable citations, annotations, and source-grounded edits need
all three of the following:

1. A document locator
2. An exact or verifiable source snapshot
3. A selector within that source

A motivating consumer scenario is Google-Docs-style commenting on Markdown: comments
live outside the document in a YAML sidecar file, each anchored by a reference, and must
survive edits to the document through exact or approximate re-anchoring.
The findings and prior-art sections below evaluate this use case directly.

This research evaluates whether these concerns should become a small standalone protocol
with Python and TypeScript implementations.
The proposed abstraction is **TextRef**, a compact composition of DocRef, SnapshotRef,
and SpanRef:

```text
TextRef
├── DocRef       requested document locator and provenance
├── SnapshotRef  normalized-text identity and optional resolved revision
└── SpanRef      optional passage selector within that text
```

The recommendation is to create one language-neutral specification and conformance suite
in a standalone repository, with thin Python and TypeScript reference implementations.
The core should be pure and dependency-free.
Filesystem, network, Git, rendering, and application policy should remain in
consumer-owned adapters.

## Questions to Answer

1. What problem should the shared reference protocol solve, and which adjacent problems
   should remain outside it?
2. How do tbd’s DocRef and FlexDoc’s SpanRef currently behave?
3. Which parts of their behavior are stable contracts, implementation policies, or
   unresolved gaps?
4. What relevant standards and existing formats should be reused or avoided?
5. Should the portable form be a URI-like string, a structured object, or both?
6. How should document location, snapshot identity, and passage selection compose?
7. What semantics must be identical across Python and TypeScript?
8. Which decisions require further design or empirical validation before extraction?
9. Does prior art exist for out-of-band (sidecar) annotations over editable text, and
   does the proposed composition cover that use case?

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
Excluding annotation bodies does not exclude the sidecar-annotation use case: the
protocol supplies the target references, and the annotation schema around them is
consumer-owned.

## Terminology

- **DocRef:** A compact application reference that says where a document can be found.
  It is a requested locator and provenance record, not necessarily immutable identity.
- **SnapshotRef:** Evidence identifying one normalized source-text representation.
- **SpanRef:** A selector for one non-empty passage in already-available normalized
  source text.
- **TextRef:** A DocRef with an optional SnapshotRef and optional SpanRef.
  Without a SpanRef it refers to the whole document.
- **Resolver:** Consumer-provided code that obtains text and provenance for a DocRef.
- **Canonical source text:** The precisely normalized Unicode string against which
  snapshot hashes and SpanRef offsets are computed.

The word *reference* is intentional.
A reference may need contextual resolution and can fail.
It is not necessarily a globally unique or permanently dereferenceable identifier.

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

Current implementation details, observed by inspecting the installed tbd v0.3.0 bundles,
reveal work that extraction would need to finish:

- The source map contains parsing, formatting, normalization, and equality logic, but
  the installed package exposes no supported public DocRef API. Its internal bundled
  chunk does not export the formatter or equality helper, and normalization alone does
  not implement the documented leading-`./` equality rule.
- `tbd docs add` requires an explicit Git revision even though the base grammar permits
  an omitted revision.
  This consumer-level restriction improves reproducibility but a branch revision remains
  mutable.
- DocRef validation is not applied uniformly at every configuration boundary.
- Git resolution can discover a commit, but tbd v0.3.0 does not persist that result as a
  general snapshot record.
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

### Snapshot Identity Connects DocRef and SpanRef

DocRef and SpanRef become coherent when a snapshot record sits between them:

```text
DocRef ──resolve──> normalized source + SnapshotRef ──select──> SpanRef result
```

This resolves a subtle ambiguity in the current SpanRef contract.
A context-free offset cannot safely choose between duplicate quotes when the caller
supplies an unverified document.
If the TextRef’s snapshot hash matches the supplied normalized text, however, the offset
belongs to that exact snapshot and can identify the intended duplicate.

The proposed rule, pending confirmation as an open question, is:

- When the snapshot hash matches, a valid offset whose slice equals `exact` is
  authoritative for that snapshot.
- When the snapshot is absent or differs, the offset is only a hint and quote/context
  re-anchoring remains conservative.

Snapshot-bound TextRefs should therefore normally retain offsets.
Dropping them loses useful identity within an immutable snapshot.
The quote remains necessary for recovery after the document changes.
This intentionally reverses the earlier span-references brief’s
persist-the-quote-drop-the-offsets guidance: the snapshot hash is what makes a persisted
offset trustworthy, and that hash did not exist in the earlier design.

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

Google-Docs-style comments on a Markdown document, stored out-of-band, need every part
of the proposed protocol at once: a locator for the commented document, a snapshot
identity for cheap staleness detection, and a durable selector per comment.
A sidecar file can hoist the shared parts to the top level and use bare SpanRefs per
comment, mirroring the FlexDoc guidance that an enclosing container may supply document
and snapshot context:

```yaml
# design.md.comments.yaml -- a consumer schema over the protocol, not part of it
format: example-comments/0.1
document: ./design.md
snapshot:
  text_profile: textref-source-v1
  text_hash: "sha256:83f6d4..."
comments:
  - id: c1
    author: alice
    created: 2026-07-12T09:14:00Z
    status: open
    span:
      exact: "Canonical source is authoritative."
      prefix: "The parser guarantees that "
      suffix: " Derived views are secondary."
      start: 1842
      end: 1876
    body: Is this still true after the renderer refactor?
    replies:
      - author: bob
        body: Yes; see the revised parsing section.
```

The comment bodies, authors, threads, and resolution state are the consumer’s schema.
The protocol contributes the anchoring contract, which gives the sidecar a precise
lifecycle:

1. On save, capture each comment’s span with context, record offsets, and update the
   file-level snapshot hash.
2. On load, hash the current document text.
   If it matches the stored snapshot, every offset is authoritative and anchoring costs
   nothing.
3. If the hash differs, re-anchor each span through the resolution tiers, rewrite
   offsets, and update the snapshot.
4. A span that fails to re-anchor becomes visibly orphaned, retaining its quote and
   context for later recovery or human reconciliation.
   It must not be silently dropped or guessed into place.

The orphaned state is not hypothetical polish.
User studies of annotation systems found that when anchor text is deleted, users prefer
an honest orphan over a confident wrong guess (Brush et al., CHI 2001), and a 2015 study
of 20,953 Hypothesis annotations found about 22% already orphaned on the live web and
53% of the remainder at risk if the page changed.
Even best-in-class quote anchoring loses a meaningful fraction of anchors over time, so
the format must represent failure explicitly rather than promise lossless survival.

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

### W3C Web Annotation Provides the Best Conceptual Model

The W3C Web Annotation Data Model represents a selected resource as:

- `source`: the resource
- `state`: the intended representation of that resource
- `selector`: a segment within that representation

This maps directly to DocRef, SnapshotRef, and SpanRef.
Its TextQuoteSelector supplies `exact`, `prefix`, and `suffix`; its TextPositionSelector
supplies zero-based half-open positions.
The Recommendation mandates offsets in Unicode code points ("The selection of the text
MUST be in terms of unicode code points … not in terms of code units"), requires logical
text order, and states normatively that selections SHOULD NOT split grapheme clusters.
This corrects the earlier span-references brief, which described the offset unit as
unresolved: the residual interop hazard is implementations ignoring the requirement, not
spec silence.

The full Web Annotation JSON-LD/RDF model also covers bodies, motivations, agents,
styles, multiple resources, states, and protocol concerns.
Adopting all of it would make the common low-level reference harder to embed.
TextRef should be a small compatible profile, with a documented mapping to Web
Annotation rather than a dependency on its full representation.

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
It is still the wrong persistence format for this protocol, for reasons the details
below make concrete.
The prior [span-references research](research-2026-05-30-span-references.md) has a
compact summary and an incompatibilities-to-bridge list; this section goes deeper on
mechanics, support, and current evolution.

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
The earlier characterization to avoid is not “unstandardized” but “standardized
elsewhere”: its destination is the WHATWG HTML Living Standard, and its semantics are
browser-navigation semantics.

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

#### Support Is Universal but Recent

| Engine | Navigation support | `::target-text` | `document.fragmentDirective` |
| --- | --- | --- | --- |
| Chrome (and Chromium family) | 80 (Feb 2020; some compatibility tables list 81) | 89 | 86 |
| Edge | 83 (May 2020) | 89 | 86 |
| Safari (macOS and iOS) | 16.1 (Oct 2022) | 18.2 (Dec 2024) | 18.4 (Mar 2025) |
| Firefox (desktop and Android) | 131 (Oct 2024) | 131 | 131 |

The feature became Baseline “newly available” on 2024-10-01 when Firefox 131 shipped,
reaches Baseline “widely available” around April 2027, and covers roughly 92% of global
users as of mid-2026. Feature detection is `'fragmentDirective' in document`, with one
notable trap: Safari 16.1 through 18.3 supported navigation without exposing the API,
producing false negatives for about two and a half years.
Android WebView, WKWebView, WebView2, and Electron all inherit support, but directives
are honored only on full navigations, never on SPA route changes.
Brave, the last significant holdout, shipped with the feature disabled over privacy
objections and re-enabled it by default in 2025 after judging the spec’s mitigations
sufficient.

Creation UX is now native everywhere: Chrome 90 added “Copy Link to Highlight” (April
2021), Safari 18.2 “Copy Link with Highlight” (December 2024), and Firefox 145 the same
(November 2025). At scale, Google Search has emitted text-fragment links from featured
snippets since 2020, and Google AI Overviews citation clicks carry `#:~:text=`
fragments, which SEO tooling now uses as an AI-referral marker.
Obsidian’s Web Clipper emits them for highlights.
Safari’s matching and generation lagged the spec longest, with fixes still landing in
Safari 26 (September 2025).

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
- **Userland tooling is mature.** GoogleChromeLabs’
  [text-fragments-polyfill](https://github.com/GoogleChromeLabs/text-fragments-polyfill)
  provides both matching and generation utilities, is actively maintained, and powers
  Chrome on iOS (which cannot reuse Blink’s native implementation over WKWebView).
- **The lineage is shared.** The text directive’s quote-plus-context design and the W3C
  TextQuoteSelector descend from the same annotation-selector work, which is why a clean
  mapping from SpanRef exists at all; the Hypothesis project has discussed emitting
  text-fragment URLs for its annotations for exactly this reason.

#### Implications for TextRef

The projection from a SpanRef is straightforward but lossy and directional: `exact` maps
to `textStart` (or a `textStart,textEnd` range for long quotes), `prefix` and `suffix`
map to context terms, everything is percent-encoded (structurally `-`, `,`, `&`), and
offsets and snapshot identity drop out entirely.
An exporter must also refuse spans the format cannot express: case-significant quotes
(matching is case-insensitive), sub-word spans (word-boundary rule), terms crossing
block boundaries, and content that does not appear in rendered text.
FlexDoc already ships this projection as `SpanRef.to_text_fragment()`, which encodes the
structural delimiters correctly but projects source text directly with only a docstring
caveat about the rendered-text mismatch; its post-extraction home should be a
rendered-text adapter, not the protocol core.
The import direction, parsing `#:~:text=` into a rendered-text SpanRef, is mechanically
simple but inherits the rendered-text profile question and is out of scope for v0.1.

The persistence conclusion stands and is sharpened by the details: the format is
transient by design (the spec’s own link-lifetime guidance frames it for sharing, not
archival), matches loosely against a representation this protocol does not define,
reports nothing on failure, and has no snapshot or offset concept.
It is a valuable export target and a poor foundation.
TextRef should define exact source-grounded semantics and treat text fragments as one
well-specified, refusable projection.

### Offset and Content-Addressed Formats Solve Narrower Problems

- **RFC 5147** identifies character or line positions in `text/plain` and can attach
  integrity information.
  It detects change but does not recover from edits.
  Its MD5, clamping, and fragment syntax should not be inherited.
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

### Annotation Systems Confirm Quote-Primary Anchoring

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
  2015\) sampled 20,953 highlight annotations: about 22% were already orphaned, 53% of
  the still-attached annotations were at risk if their page changed, and only about 12%
  of orphans could be recovered from web archives.
- **Apache Annotator**, the standards-blessed implementation of W3C selector creation
  and resolution, entered the Apache Incubator in 2016 and was retired in August 2025
  with its repository archived; its matching remained exact-only, with fuzzy quote
  matching proposed but never implemented.
  The maintained lineage of working anchoring code is the Hypothesis client, not the
  standards project.
- **The research lineage is older than the web annotation tools.** Phelps and Wilensky’s
  robust intra-document locations (WWW9, 2000) store redundant independent descriptors
  (unique ID, structural tree walk, surrounding context) with ordered reattachment and
  graceful degradation.
  Brush et al. (CHI 2001) found users judge re-anchoring by the unique words of the
  anchor text and prefer honest orphans over wrong guesses; the companion Microsoft tech
  report proposes keyword anchoring (rarest words plus inter-keyword distances), which
  tolerates rewording that defeats exact-quote matching and is a plausible future
  evidence type for approximate strategies.
- **diff-match-patch itself is now legacy.** The Google repository was archived in
  August 2024; a maintained Python fork exists, but its Bitap matcher still caps
  patterns at the machine word.
  New implementations should prefer the Myers 1999 approach for long quotes.

The protocol’s resolution tiers, conservative ambiguity handling, and visible failure
axis match this consensus.
What the prior systems lack, and SnapshotRef adds, is cheap change detection: Hypothesis
has no stored document hash, so it cannot distinguish “unchanged, trust offsets” from
“changed, must re-anchor” without re-deriving the text.

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
  snapshot hash detects.
  Line- and diff-anchored review comments (GitHub’s `position`, Gerrit patch sets) are
  the canonical demonstration that positional anchors decay: GitHub marks them
  “outdated” and hides them, and Gerrit re-derives positions by diffing revisions, an
  option unavailable to a sidecar that meets only the current document.

### No Portable Sidecar Format for Markdown Comments Exists

Searching for prior art on the specific target use case, Google-Docs-style comments on
Markdown stored out-of-band, found no established format, only partial approaches:

- **Inline syntaxes change the document.** CriticMarkup (`{>>comment<<}`,
  `{==highlight==}`) anchors perfectly because the markers live in the text, but it
  pollutes diffs, renders as garbage in tools that do not support it, and carries no
  threading or resolution model.
  HTML comments and Obsidian `%%` comments share the problem.
  iA’s Markdown Annotations spec (v0.2) appends an annotation block to the file anchored
  by grapheme-cluster offsets plus a SHA-256 hash; the hash detects edits but nothing
  repairs the offsets, and adoption never spread beyond iA.
- **Polished commenting experiences are platform-locked.** HackMD, StackEdit, GitBook,
  and Google Docs all offer selection-anchored threads, and none produces a portable
  artifact next to the Markdown.
  Google Docs is instructive: comments ride the internal revision history, the Drive API
  documents comment anchors as immutable and revision-bound with no positional guarantee
  between revisions, and the 2024 native Markdown import/export carries content only, so
  comments do not survive the round trip.
  Edit-history anchoring works only inside the system that recorded the edits.
- **CRDT anchors are the same story in stronger form.** Peritext (Ink and Switch)
  anchors comment spans to stable per-character operation IDs with tombstones, so
  anchors never dangle inside the CRDT, and ProseMirror, Yjs, and Automerge each provide
  positions that transform through edits.
  All are perfectly durable and completely non-portable: a plain Markdown file on disk
  has no operation IDs.
  Content-based re-anchoring is the only option for files edited by arbitrary tools,
  which is exactly the situation of a git-tracked document edited by people and agents.
- **The closest packaging prior art is MRSF (“Sidemark”),** a 2026 single-maintainer
  Markdown Review Sidecar Format: threaded, resolvable comments in a
  `<doc>.md.review.yaml` sidecar with JSON Schema, CLI, MCP server, and VS Code tooling
  ([spec](https://github.com/wictorwilen/MRSF)). Its anchors store line/column
  coordinates, the selected text (with a SHA-256 hash of that selection), and an
  optional git commit for staleness; re-anchoring falls back from exact text match
  through line/column plausibility to contextual search, ending in an explicit orphaned
  state. MRSF validates both the demand and the sidecar packaging, but its anchor model
  is weaker than the composition proposed here: no prefix/suffix context to disambiguate
  duplicate quotes, staleness detection tied to git commits rather than a normalized
  document hash, and line/column coordinates rather than text offsets as the positional
  evidence.
- **LLM-era systems are converging on the same design.** Semiont (AI Alliance) stores
  dual selectors per annotation (quote plus position), reconciles them at write time,
  re-anchors on verbatim quote match with context recovery, and flags failures
  low-confidence instead of guessing.
  Codetations (2025) keeps notes out-of-document and combines edit-tracking while an
  editor is live with LLM-assisted re-anchoring for offline edits, and reports that
  anchored annotations improve LLM code-repair performance.
  Agent-facing Markdown review tools appearing through 2025 and 2026 (md-annotator,
  md-review, and Google-Docs automation workarounds for the Drive API anchor limitation)
  all show demand for a portable, content-anchored comment format.

The gap is specific: nothing found combines a document locator, a normalized-snapshot
hash independent of any version-control system, and a quote-primary selector with
defined re-anchoring in a diffable sidecar.
Each piece exists separately; the composition does not, which is the case for defining
it once as a protocol.

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

**Description:** tbd owns DocRef, FlexDoc owns SpanRef, and applications compose them ad
hoc.

**Advantages:**

- No new repository or release process
- Minimal immediate migration
- Each project can evolve independently

**Disadvantages:**

- No shared snapshot or top-level reference contract
- TypeScript and Python behavior can diverge
- tbd cannot reuse SpanRef without depending on a larger Python document library
- FlexDoc would need to duplicate or depend on tbd’s TypeScript-specific DocRef logic
- Cross-tool persisted references have no independent owner

This remains reasonable only if the two systems never exchange references.
Their planned annotation, review, and source-grounded editing work makes that unlikely.

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

A compact string projection could be added after the object model stabilizes.
It should not be the normative v0.1 representation.

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
representation boundary: v0.1 refers to text, not arbitrary binary resources or rendered
layout.

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
- `snapshot` is optional.
  If present, `text_profile` and `text_hash` are required and `revision` is optional.
- `span` is optional. Its absence means the whole document.
- A TextRef containing `span` has no independently recognized Git or URL fragment.
  The final DocRef rules must define this per kind before it is enforced.
- `exact` is required and contains at least one Unicode code point.
- `prefix` and `suffix` are optional, non-empty immediate context strings.
- `start` and `end` are both present or both absent.
- Positions are non-negative JSON-safe integers, use Unicode code points, and form a
  start-inclusive, end-exclusive interval.
- When positions are present, `end - start` equals the code-point length of `exact`.
- The provisional recommendation is to reject unknown top-level fields while allowing
  future optional data under a defined, namespaced extension container.
  The final rule remains an explicit compatibility decision.

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
before schema validation.
YAML-specific scalar types or independent semantics are not part of the protocol.

### Canonical Source Profile

The core resolver accepts a Unicode string; byte decoding is an adapter responsibility.
Every snapshot names the profile used to compute its hash.
The proposed `textref-source-v1` profile is:

1. Require Unicode scalar values and reject unpaired surrogates.
2. Convert CRLF and lone CR to LF.
3. Preserve all other code points exactly.
4. Do not normalize Unicode, case, whitespace, BOM, or final newlines.
5. Compute `text_hash` over the normalized string encoded as UTF-8.

Under this proposal, a BOM is retained as text, NEL/U+2028/U+2029 are not treated as
line endings, and the presence or absence of a final newline is preserved.
Before v0.1, these compatibility choices should be confirmed because changing any of
them changes offsets and hashes.
Byte-oriented adapters must separately define their accepted encodings and decoding
failures.

The digest string should include its algorithm.
RFC 6920 can inform equality, but the field should be named `text_hash`, not HTTP
`Content-Digest` or `Repr-Digest`, because its input is an application-normalized source
string. Snapshot identity is the tuple of text profile, digest algorithm, digest length,
and digest value; `revision` is resolver provenance unless the final specification
explicitly gives it stronger semantics.

### Resolution Semantics

Resolution separates document acquisition from passage selection:

1. Parse and normalize the DocRef without I/O.
2. Ask a consumer-owned resolver for decoded source text and provenance.
3. Apply the canonical source profile and compute the actual text hash.
4. Compare the expected and actual snapshot.
5. Resolve the SpanRef, if present.
6. Return a typed result containing the snapshot status, selection outcome, and method.

Recommended exact-selection tiers:

1. **Snapshot-bound position:** If hashes match and `[start, end)` equals `exact`,
   accept the position even when the quote occurs elsewhere.
2. **Corroborated position:** Without a matching hash, accept a position only when the
   quote and non-empty captured context corroborate it.
3. **Exact quote search:** Resolve a unique exact occurrence.
4. **Context disambiguation:** Resolve one duplicate only when context uniquely
   identifies it.
5. **Visible failure:** Report missing or ambiguous rather than choosing arbitrarily.

Approximate, case-normalized, or whitespace-normalized matching should be an optional
strategy with a named method and score.
It should not change exact v0.1 behavior.

The result should keep independent axes rather than flattening a stale but successfully
re-anchored reference into one status:

| Axis | Suggested Values |
| --- | --- |
| Document | `resolved`, `unavailable`, `invalid` |
| Snapshot | `absent`, `matched`, `mismatched` |
| Span | `whole_document`, `resolved`, `missing`, `ambiguous` |
| Method | `snapshot_position`, `context_position`, `exact_quote`, `context_quote`, `none` |

A convenience nullable API may wrap these results, but persisted tools and edit
workflows need the distinctions.
A `resolve_all` API can expose candidates while `resolve_one` preserves conservative
single-target semantics.

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

Resolvers must separately enforce filesystem roots, allowed schemes and hosts, redirect
limits, response-size limits, timeouts, and credential handling.
Keeping I/O outside the core reduces both dependencies and security exposure.

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
- Matching, absent, and stale snapshots
- Maximum JSON-safe offsets
- Unknown and duplicate JSON members

### Integration With tbd

tbd should use the TypeScript package for its existing DocRef boundaries first.
That integration should:

- Preserve the current DocRef v0.1 spelling where deliberately compatible
- Export and test the public parser, formatter, normalizer, and equality API
- Validate every DocRef-bearing configuration field consistently
- Fix local absolute-path resolution as a consumer issue
- Keep `spec_path` and managed-document `kind + name` identity unchanged
- Add SnapshotRef only where resolved provenance or reproducibility is needed
- Add TextRef only to fields that actually target passages, such as future review
  findings or source citations

Managed-doc caching does not need a SpanRef.
Whole-document features should continue using DocRef or TextRef without `span`.

### Integration With FlexDoc

FlexDoc should use the Python package for SpanRef and snapshot primitives while keeping
FlexDoc-specific adapters locally:

- Keep `SpanRef.from_node()` in FlexDoc
- Re-export the standalone SpanRef only after deciding API and pickle compatibility
- Revisit the `to_persisted()` offsets-dropped default for snapshot-bound references,
  per the snapshot-authority rule above
- Move `SpanRef.to_text_fragment()` to a rendered-text adapter with explicit refusal
  rules, since it currently projects source text directly
- Preserve `DocGraph/v0.1`
- Add document locator, snapshot, and typed annotation targets in an explicit later
  schema version
- Use bare SpanRef for annotations embedded in a DocGraph whose enclosing source already
  supplies document and snapshot context
- Use complete TextRef for annotations detached from a graph or targeting another
  document

The protocol decision should precede Phase 2 work on annotation ownership, batch
resolution, and snapshot-aware suggested edits.
Rendered browser fragments remain a separate FlexDoc adapter concern.

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
    retain non-empty quote-only spans?
    Supporting both likely requires a distinct PositionRef.
12. **Context policy:** Is context length a normative construction rule or caller
    policy? A shared default is convenient, but hard-coding 24 characters into the wire
    contract is unnecessary.
13. **Context semantics:** Should stale context be advisory when `exact` is unique, as
    FlexDoc behaves today, or a strict constraint whenever supplied?
14. **Snapshot-bound positions:** Confirm that a matching hash makes a verified offset
    authoritative among duplicate quotes.
15. **Grapheme boundaries:** Should validation reject spans that split a grapheme
    cluster, warn, or document a justified deviation from the Web Annotation model’s
    normative SHOULD NOT?
16. **Approximate matching:** Which normalized or fuzzy strategies, if any, deserve
    standardized names and conformance vectors?
17. **Immutability:** Should resolution return an updated immutable SpanRef rather than
    mutate positions in place?
18. **Discontinuous selections:** Are multiple spans one TextRef collection, an
    annotation concern, or a future selector type?

### Annotation Sidecar Composition

19. **Sidecar hoisting:** May a consumer container hoist `document` and `snapshot` to
    the file level above many bare SpanRefs, as the sidecar example does, and should the
    protocol define that composition rule or leave it entirely to consumers?
20. **Orphan representation:** Should the resolution result define a persistable
    orphaned state and a confidence score for approximate methods, so independent
    sidecar tools share failure semantics instead of inventing their own?
21. **Web Annotation round-trip:** Should the specification include a normative mapping
    from sidecar annotations to W3C Web Annotation JSON so anchors can move between
    sidecars and annotation stores?

### Safety, Privacy, and Evolution

22. **Quote limits:** What maximum `exact`, prefix, suffix, document size, and candidate
    count prevent denial of service and accidental copying of large copyrighted or
    sensitive passages?
23. **Extension behavior:** Reject unknown fields for typo safety, ignore them for
    forward compatibility, or require all extensions under a namespaced container?
24. **Versioning:** What changes are compatible within `textref/0.x`, and when does a
    new major become necessary?
25. **Governance:** Who owns releases and adjudicates behavior changes when tbd and
    FlexDoc need different policies?
26. **Package compatibility:** Does FlexDoc preserve the current import/module identity
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
11. Define the approximate re-anchoring cascade and an explicit orphaned outcome as a
    named optional strategy, informed by Hypothesis’s production scoring and the
    annotation-positioning literature, so sidecar annotation tools share failure
    semantics.
12. Validate the sidecar annotation profile against MRSF and the W3C Web Annotation
    model, and document a mapping to each.

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
- [ ] Prototype a YAML comment-sidecar consumer profile over TextRef and compare it
  against MRSF and a Web Annotation mapping
- [ ] Add rendered-text and fuzzy-resolution adapters only after source-text v0.1 is
  stable

## Methodology

This research reviewed:

- tbd v0.3.0 managed DocRef and docmap documentation
- The installed tbd TypeScript bundles for parsing, caching, fork manifests, and public
  exports
- FlexDoc’s SpanRef, DocGraph source metadata, tests, design specification, and active
  roadmap
- Existing project research on stable span references, document models, and multilayer
  parsing
- Primary W3C, WICG, IETF, IANA, ECMAScript, Package URL, and Software Heritage sources
- Primary WICG/WHATWG spec text, MDN, caniuse, webstatus.dev, and browser release notes
  for text-fragment mechanics and support, with claims adversarially verified against
  those sources
- Annotation-system prior art: the Hypothesis client source and blog, the W3C Web
  Annotation Recommendations, MRSF, standoff formats (brat, STAM, WebAnno), CRDT
  anchoring designs (Peritext, Yjs, Automerge), and the annotation-positioning
  literature (Phelps and Wilensky 2000; Brush et al.
  2001)

No implementation spike or performance benchmark was performed.
Algorithm and package recommendations are design conclusions; context-size,
fuzzy-matching, and large-document limits still require empirical validation.

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
- [MDN: Text fragments](https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Fragment/Text_fragments)
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
- [RFC 7493: I-JSON](https://www.rfc-editor.org/rfc/rfc7493.html)
- [RFC 7595: URI Scheme Guidelines](https://www.rfc-editor.org/rfc/rfc7595.html)
- [IANA URI Scheme Registry](https://www.iana.org/assignments/uri-schemes/uri-schemes.xhtml)
- [RFC 7763: The `text/markdown` Media Type](https://www.rfc-editor.org/rfc/rfc7763.html)
- [RFC 8259: JSON](https://www.rfc-editor.org/rfc/rfc8259.html)
- [RFC 8820: URI Design and Ownership](https://www.rfc-editor.org/rfc/rfc8820.html)
- [RFC 9530: Digest Fields](https://www.rfc-editor.org/rfc/rfc9530.html)
- [ECMAScript String Type](https://tc39.es/ecma262/#sec-ecmascript-language-types-string-type)
- [Package URL specification (ECMA-427)](https://ecma-international.org/publications-and-standards/standards/ecma-427/)
- [SWHID specification (ISO/IEC 18670:2025)](https://www.swhid.org/)
- [Hypothesis: fuzzy anchoring](https://web.hypothes.is/blog/fuzzy-anchoring/)
- [Hypothesis client quote matching](https://github.com/hypothesis/client/blob/main/src/annotator/anchoring/match-quote.ts)
- [Quantifying Orphaned Annotations in Hypothes.is](https://arxiv.org/abs/1512.06195)
- [approx-string-match](https://github.com/robertknight/approx-string-match-js)
- [diff-match-patch (archived 2024)](https://github.com/google/diff-match-patch)
- [Apache Annotator (retired 2025)](https://github.com/apache/incubator-annotator)
- [Phelps and Wilensky: Robust Locations for Annotation](https://www.dlib.org/dlib/july00/wilensky/07wilensky.html)
- [Brush et al.: Robust Annotation Positioning in Digital Documents](https://dl.acm.org/doi/10.1145/365024.365117)
- [Brush and Bargeron: Robustly Anchoring Annotations Using Keywords](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr-2001-107.pdf)
- [brat standoff annotation format](https://brat.nlplab.org/standoff.html)
- [STAM: Stand-off Text Annotation Model](https://annotation.github.io/stam/)
- [SARIF v2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
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
