# Changelog

All notable changes to flexdoc are documented here.
This project uses [semantic versioning](https://semver.org/); while pre-1.0, breaking
changes bump the **minor** version (see `docs/publishing.md`).

## Unreleased

This is an intentional pre-1.0 API break and requires a minor release (expected 0.4.0),
not a 0.3.x patch.

### Added

- **Cross-language logical word metrics.** `TextUnit.logical_words` measures normalized
  word-equivalent volume across natural language, CJK text, source code, URLs, and other
  punctuation-dense content. `flexdoc.util.logical_word_count()` exposes the same
  dependency-free primitive, while `raw_word_count()` preserves literal
  whitespace-delimited counting.

### Changed

- **`TextUnit.words` is replaced by explicit raw and logical units.** Most callers
  should migrate to `TextUnit.logical_words`; callers that require the exact previous
  whitespace-split behavior should use `TextUnit.raw_words`. No deprecated alias is
  retained. Size summaries, section-tree defaults, and debug reports now use logical
  words, and aggregate counts are rounded only after the full text is measured.
- **Approximate token estimates now scale logical words.** `estimate_tokens()` uses
  `TOKENS_PER_LOGICAL_WORD` (default `1.6`) instead of the former
  `CHARS_PER_TOKEN`/`chars_per_token` API. This is still a model-family heuristic; use
  the target provider's tokenizer for exact counts or hard context limits.
- **Reading-time guidance is language-robust.** Pass logical word counts to
  `format_read_time()`; the default rate corresponds to roughly 450 CJK characters per
  minute under the default wide-character weight.

## 0.3.0 (2026-07-11)

Fixes from the 2026-07 pre-promotion design review
(`docs/project/review/senior-engineering-review-flexdoc-2026-07.md`). These changes
alter documented behavior, so per the pre-1.0 rule this is a minor release, not a
0.2.x patch.

### Fixed

- **CRLF input no longer corrupts the structural views.** marko computes block positions
  against LF-only text, so `\r` in the input desynchronized every structural span
  (`blocks()`, `sections()`, `base_blocks()`, `links()`, `prose_text()`, the node table)
  from `source_text`, silently garbling content and violating the base-block cover
  invariant. `from_text` now normalizes `\r\n` and lone `\r` to `\n` and retains the
  normalized string as `source_text`, so all layers share one offset space.
  Callers anchoring offsets to an external CRLF original must normalize it the same way
  first.
- **Markdown constructs inside frontmatter can no longer swallow the body.** The shared
  parse previously included the frontmatter region, so e.g. a YAML block scalar
  containing a code fence opened a fenced block spanning the rest of the document,
  leaving `blocks()` empty.
  The frontmatter region is now blanked out of the shared parse (offsets preserved);
  frontmatter remains a non-content region.
  Link extraction now reuses that blanked parse instead of reparsing the body for
  frontmatter documents.
- **`resolve()` no longer guesses on ambiguous quotes.** Per the spec’s error posture
  (§11), a `SpanRef` quote that occurs multiple times with no disambiguating
  prefix/suffix (or a tied context score) now resolves to `None` instead of silently
  anchoring to the first occurrence.
  A context-free position hint also cannot select a duplicate, because no context or
  source identity proves which occurrence was intended.
  A zero-width quote (`exact=""`) also resolves to `None` on both the fast and slow
  paths.
- **`collect(overlaps=...)` treats empty intervals as empty.** A degenerate `[x, x)`
  region (or node span) now overlaps nothing, matching half-open interval semantics;
  point queries use `(x, x + 1)`.
- **Render helpers harden their HTML output.** `render_node_attrs` attribute-escapes
  `node.id`, and `wrap_with_node_attrs` validates the tag name (raising `ValueError`),
  matching the validation in the `flexdoc.html` tag helpers.

### Changed

- **The dependency lock is refreshed under the 14-day cool-off.** The cutoff is
  2026-06-26, expired per-package exceptions are removed, and the audit group resolves
  fixed `pip` and `msgpack` versions, so CI runs `pip-audit` without advisory ignores.
- **`graph()` accepts any set.** `FlexDoc.graph()` and `build_doc_graph()` annotate
  `include`/`detail` as `collections.abc.Set`, so plain `set` literals type-check
  (matching `collect()`); behavior is unchanged.
- **`TextUnit` is a `StrEnum`**, matching every other public enum, so
  `TextUnit.words == "words"` now holds.
  Source-compatible for enum-member access; only `str()`/equality-with-string behavior
  changes.
- **Recursive `collect()` includes inline descendants by default.** The `inline`
  parameter is now tri-state: omission follows recursive traversal or an explicit
  inline-kind filter, `inline=False` excludes inline nodes, and `inline=True` includes
  them for any query. Callers that need the previous block-only recursive result must
  pass `inline=False`.
- **Cached structural views are mutation-safe.** `Block` is now frozen, `Block.children`
  and `TableInfo.alignments` are tuples, and `sections()` returns recursively isolated
  section/paragraph copies.
  Code constructing blocks directly must pass child tuples; code comparing or building
  table metadata must use alignment tuples.
  Mutation of a returned section remains local to that view and does not persist to a
  later call.
- **`SpanRef` owns its public resolution API.** Call `ref.resolve(source_text)` or
  `ref.resolve_and_update(source_text)` on the root-exported type.
  The generic `resolve` and `resolve_and_update` names are no longer promoted from
  `flexdoc.docs`; update package-level imports and calls to use the methods.
- **Paragraph heading metadata is property-based.** `Paragraph.heading_level` and
  `Paragraph.heading_title` now match `Paragraph.block_type` and `Block.heading_level`.
  Remove `()` from calls to the two former methods.
- **The navigable-link constant is accurately named.** Import `NAVIGABLE_LINK_FORMS`
  instead of `TRUE_LINK_FORMS`; no compatibility alias is retained.
- **`flexdoc.docs` now promotes the document model only.** Word-token/search and
  diff/mapping names are no longer re-exported.
  Import them from `flexdoc.docs.wordtoks`, `search_tokens`, `token_diffs`, or
  `token_mapping` instead.
  The current Chopdiff integration already uses these owning-module paths.
- **Frontmatter delimiters tolerate trailing horizontal whitespace.** Opening and
  closing `---` lines may end in spaces or tabs while remaining verbatim in
  `frontmatter`; leading whitespace still disqualifies a delimiter, and an unclosed
  opening remains a thematic break.
- **The OS-independent classifier is backed by macOS CI.** Ubuntu still covers every
  supported Python version, and Python 3.13 now runs the full lint/test gate on
  `macos-latest` as a representative second platform.
- **Local release preparation is tag-aware.** The runbook fetches tags before building
  and verifies candidate wheel metadata from an isolated local tag, preventing a tagless
  clone from silently producing a `0.0.1.devN` release artifact.
- **Section sizing no longer constructs temporary documents.** `FlexDoc` and `Section`
  now share private paragraph aggregation for every `TextUnit` and size summary; public
  results and signatures are unchanged.

Remaining pre-1.0 design decisions and future mechanisms are collected in
`docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md`.

## 0.2.0 (2026-06-14)

Correctness fixes and a completed inline/heading/link surface for the document-metrics
use case (`docs/project/specs/active/plan-2026-06-13-metrics-use-case.md`, issue #6). As
a preview-stage library this takes the cleanest shape with no compatibility shims; the
API additions below include breaking signature changes (see **Changed**).

### Fixed

- **`node_table()` / `collect()` / `graph()` no longer raise on valid Markdown.** Inline
  elements were discovered over the whole source and parented by start offset, so
  backtick pairing across a block boundary (an empty fence next to inline backticks)
  produced an inline span escaping its parent block and raised a layer-nesting error.
  Inline discovery is now scoped per leaf content block, so an inline node can never
  straddle a block boundary; links/images/definitions are parented by full containment.
- **`sections()` / `toc()` recover every heading `blocks()` finds, and own their content
  correctly.** Headings were re-derived from the blank-line paragraph view, dropping
  tight headings and headings preceded by a non-blank line (e.g. an HTML-comment
  marker), and section content was bucketed from that same view, so a heading glued to
  its body lost the body.
  Sections now derive entirely from the structural block tree—the heading set *and* each
  section’s own content (`own_paragraphs()` / `blocks()` / sizes) come from the
  section’s source region—so tight and marker-preceded headings own exactly their
  content.
- **Section spans nest correctly** even when a blank-line paragraph straddles a later
  heading (e.g. an embedded `---` block marko reads as a setext heading): each section
  spans from its heading to the next same-or-higher heading (trimmed), which nests by
  construction. Byte-identical to the prior span for well-formed documents.
- **Reference-definition nodes attach to their block.** A `link_ref_def` span included
  the line’s trailing newline and escaped the containing paragraph, leaving the node
  unparented so a block-scoped `collect()` missed it; spans are now trimmed like every
  structural block.

### Added

- **Heading metadata on the structural block**: `Block.heading_info` (`HeadingInfo` with
  parser-authoritative `level` and `title`) and the `Block.heading_level` convenience;
  `HeadingInfo` is exported from `flexdoc.docs`. The node table reads heading level from
  it.
- **Typed link forms**: `LinkForm` (`inline` / `reference` / `autolink` / `bare_url` /
  `image` / `reference_definition`) and `Link.link_form`. `FlexDoc.links(link_forms=…)`
  selects any forms (default: navigable links only), and `FlexDoc.images()` is a
  convenience for image access.
  Reference definitions (`[id]: url`) are surfaced as `NodeKind.link_ref_def` nodes and
  via `links(link_forms={LinkForm.reference_definition})`.
- **`FlexDoc.prose_text()`**: prose-only text for editorial linting and prose metrics —
  prose blocks (paragraphs/headings, and table cells when `include_tables=True`) with
  inline code and footnote refs dropped, links/images replaced by their text/alt,
  inline-HTML tags dropped (wrapped text kept), and heading/blockquote/list markers and
  reference-definition lines stripped; from verbatim source slices (line wrapping
  preserved, never reflowed) so spacing like a spaced em-dash is kept exactly.
- **`FlexDoc.block_at_offset()`**: the innermost structural `Block` containing an offset
  (the structural counterpart of `paragraph_at_offset`; the name, freed in 0.1.0, now
  correctly returns a `Block`).
- **Test-suite hardening**: adversarial corpus documents (`inline_pathology`,
  `heading_edges`, `link_taxonomy`); cross-projection invariants tying `toc()` to the
  heading blocks, inline nesting on the query surface, and link-form accounting; and a
  dogfood test that parses every Markdown file in the repo and asserts the invariants.
  See the spec’s “Why These Bugs Escaped the Tests” analysis.

### Changed

These are breaking, made cleanly (no aliases) given the preview status:

- **`Link` gains a required `link_form: LinkForm` field.** Direct `Link(...)`
  construction must pass it.
- **`block_links()` returns all link-like constructs** (navigable links, images, and
  reference definitions), each with a `link_form`; previously it returned navigable
  links only. `FlexDoc.links()` filters to navigable links by default, so its default
  result is unchanged.
- **`collect()` returns inline-kind nodes without `recursive=True`.** An inline-kind
  request (e.g. `collect(kinds={NodeKind.link})`) now widens the candidate set instead
  of silently returning `[]`—matching the documented behavior.

## 0.1.0 (2026-06-12)

First release.

### Added

- **Initial flexdoc package**, extracted from
  [chopdiff](https://github.com/jlevy/chopdiff) as its own standalone distribution.
  This is the document/markdown layer—`FlexDoc`, paragraphs/sentences, the block tree
  and block types, sections, the node table, `collect()`, `DocGraph`, `SpanRef`, token
  diffs/mappings, word tokenization, html-in-md, and read-time/token estimation—with no
  dependency on chopdiff’s diff and windowed-transform machinery.

  The import roots are `flexdoc.docs`, `flexdoc.html`, and `flexdoc.util`. Parse
  behavior is unchanged from the `flexdoc.*` modules that previously shipped inside the
  chopdiff wheel; this release packages them independently.
  See `docs/project/specs/active/plan-2026-06-11-flexdoc-extraction.md`.

- **A deliberate root API**: the working set is importable from the package root —
  `FlexDoc`, `DocGraph`, `Detail`, `SpanRef`, `BlockType`, `NodeKind`, `Layer`,
  `TextUnit`—designed against the known downstream users and pinned by contract tests.
  The render helpers for source-linked HTML (`render_node_attrs`,
  `wrap_with_node_attrs`, `parse_source_span_attr`) are public in `flexdoc.docs`.

- **DocGraph paragraph view**: `Views.paragraphs` joins `toc`/`blocks`/`links`/
  `sentences` in the serialized projection.

### Changed (Relative to the Modules as Shipped in Chopdiff)

The first standalone release also refines the API surface (the pre-publish design
review, `docs/project/review/senior-engineering-review-flexdoc-standalone-2026-06.md`);
these are intentional hard cuts with no compatibility aliases:

- **`TextDoc` is renamed `FlexDoc`**—the package’s single entry point, named for the
  model it carries (all layered projections hang off it).
  It is importable from the package root: `from flexdoc import FlexDoc`. The module is
  `flexdoc.docs.flex_doc` (was `chopdiff.docs.text_doc`), and the design of record is
  now `docs/flexdoc-spec.md` (was `textdoc-spec.md`).
- **`collect()` is fully keyword-only and the deprecated aliases are gone**: use
  `subtree_of=` (was `scope=`, previously also positional) and `within=` (was
  `contains=`).
- **Editing-view methods are named in paragraph terms**, so “block” always means the
  structural layer: `FlexDoc.paragraph_at_offset` (was `block_at_offset`),
  `FlexDoc.iter_paragraphs` (was `iter_blocks`), `Section.own_paragraphs`/
  `subtree_paragraphs` (were `own_blocks`/`subtree_blocks`).
- **The export surface is settled**: `flexdoc.docs` now exports
  `CodeInfo`/`TableInfo`/`ListInfo`, `resolve`/`resolve_and_update`,
  `parse_blocks`/`walk_blocks`/`block_type_for`, and `DEFAULT_INCLUDE`; `flexdoc.html`
  exports `html_p`, `html_tag`, `escape_attribute`, `tag_wrapper`, and
  `identity_wrapper`. Link extraction is public as `flexdoc.docs.links.block_links`.
- **`Node.attrs` values are JSON-typed** (`AttrValue`), validated at `DocGraph`
  serialization, and node-id assignment order is pinned and tested for cross-language
  ports; layer nesting guarantees (`LAYER_NESTING`) are enforced at node-table build.
- Internally, the former `text_doc.py` was split into `flex_doc.py`, `paragraphs.py`,
  `links.py`, and `sections.py` (package imports from `flexdoc.docs` are unaffected),
  and `sections()` is now cached like the other derived views.

Migration from chopdiff in one pass: `chopdiff.docs.TextDoc` → `flexdoc.FlexDoc` (or
`flexdoc.docs.FlexDoc`), `chopdiff.docs.*` → `flexdoc.docs.*`, plus the method renames
above.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
