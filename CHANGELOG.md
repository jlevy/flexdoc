# Changelog

All notable changes to flexdoc are documented here.
This project uses [semantic versioning](https://semver.org/); while pre-1.0, breaking
changes bump the **minor** version (see `docs/publishing.md`).

## 0.2.0 (unreleased)

Correctness fixes and a completed inline/heading/link surface for the document-metrics
use case (`docs/project/specs/active/plan-2026-06-13-metrics-use-case.md`, issue #6).
As a preview-stage library this takes the cleanest shape with no compatibility shims;
the API additions below include breaking signature changes (see **Changed**).

### Fixed

- **`node_table()` / `collect()` / `graph()` no longer raise on valid Markdown.** Inline
  elements were discovered over the whole source and parented by start offset, so backtick
  pairing across a block boundary (an empty fence next to inline backticks) produced an
  inline span escaping its parent block and raised a layer-nesting error. Inline discovery
  is now scoped per leaf content block, so an inline node can never straddle a block
  boundary; links/images/definitions are parented by full containment.
- **`sections()` / `toc()` recover every heading `blocks()` finds, and own their content
  correctly.** Headings were re-derived from the blank-line paragraph view, dropping tight
  headings and headings preceded by a non-blank line (e.g. an HTML-comment marker), and
  section content was bucketed from that same view, so a heading glued to its body lost the
  body. Sections now derive entirely from the structural block tree — the heading set *and*
  each section's own content (`own_paragraphs()` / `blocks()` / sizes) come from the section's
  source region — so tight and marker-preceded headings own exactly their content.
- **Section spans nest correctly** even when a blank-line paragraph straddles a later
  heading (e.g. an embedded `---` block marko reads as a setext heading): each section
  spans from its heading to the next same-or-higher heading (trimmed), which nests by
  construction. Byte-identical to the prior span for well-formed documents.
- **Reference-definition nodes attach to their block.** A `link_ref_def` span included the
  line's trailing newline and escaped the containing paragraph, leaving the node unparented
  so a block-scoped `collect()` missed it; spans are now trimmed like every structural block.

### Added

- **Heading metadata on the structural block**: `Block.heading_info` (`HeadingInfo` with
  parser-authoritative `level` and `title`) and the `Block.heading_level` convenience;
  `HeadingInfo` is exported from `flexdoc.docs`. The node table reads heading level from it.
- **Typed link forms**: `LinkForm` (`inline` / `reference` / `autolink` / `bare_url` /
  `image` / `reference_definition`) and `Link.link_form`. `FlexDoc.links(link_forms=…)` selects any
  forms (default: navigable links only), and `FlexDoc.images()` is a convenience for image
  access. Reference definitions (`[id]: url`) are surfaced as `NodeKind.link_ref_def` nodes
  and via `links(link_forms={LinkForm.reference_definition})`.
- **`FlexDoc.prose_text()`**: prose-only text for editorial linting — prose blocks with
  inline code dropped, links/images replaced by their text/alt, inline-HTML tags dropped
  (wrapped text kept), reference-definition lines excluded, from verbatim source slices so
  spacing like a spaced em-dash is preserved.
- **`FlexDoc.block_at_offset()`**: the innermost structural `Block` containing an offset
  (the structural counterpart of `paragraph_at_offset`; the name, freed in 0.1.0, now
  correctly returns a `Block`).
- **Test-suite hardening**: adversarial corpus documents (`inline_pathology`,
  `heading_edges`, `link_taxonomy`); cross-projection invariants tying `toc()` to the
  heading blocks, inline nesting on the query surface, and link-form accounting; and a
  dogfood test that parses every Markdown file in the repo and asserts the invariants. See
  the spec's "Why These Bugs Escaped the Tests" analysis.

### Changed

These are breaking, made cleanly (no aliases) given the preview status:

- **`Link` gains a required `link_form: LinkForm` field.** Direct `Link(...)` construction must
  pass it.
- **`block_links()` returns all link-like constructs** (navigable links, images, and
  reference definitions), each with a `link_form`; previously it returned navigable links only.
  `FlexDoc.links()` filters to navigable links by default, so its default result is
  unchanged.
- **`collect()` returns inline-kind nodes without `recursive=True`.** An inline-kind
  request (e.g. `collect(kinds={NodeKind.link})`) now widens the candidate set instead of
  silently returning `[]` — matching the documented behavior.

## 0.1.0 (2026-06-12)

First release.

### Added

- **Initial flexdoc package**, extracted from
  [chopdiff](https://github.com/jlevy/chopdiff) as its own standalone distribution.
  This is the document/markdown layer — `FlexDoc`, paragraphs/sentences, the block tree
  and block types, sections, the node table, `collect()`, `DocGraph`, `SpanRef`, token
  diffs/mappings, word tokenization, html-in-md, and read-time/token estimation — with
  no dependency on chopdiff’s diff and windowed-transform machinery.

  The import roots are `flexdoc.docs`, `flexdoc.html`, and `flexdoc.util`. Parse
  behavior is unchanged from the `flexdoc.*` modules that previously shipped inside the
  chopdiff wheel; this release packages them independently.
  See `docs/project/specs/active/plan-2026-06-11-flexdoc-extraction.md`.

- **A deliberate root API**: the working set is importable from the package root —
  `FlexDoc`, `DocGraph`, `Detail`, `SpanRef`, `BlockType`, `NodeKind`, `Layer`,
  `TextUnit` — designed against the known downstream users and pinned by contract
  tests. The render helpers for source-linked HTML (`render_node_attrs`,
  `wrap_with_node_attrs`, `parse_source_span_attr`) are public in `flexdoc.docs`.

- **DocGraph paragraph view**: `Views.paragraphs` joins `toc`/`blocks`/`links`/
  `sentences` in the serialized projection.

### Changed (relative to the modules as shipped in chopdiff)

The first standalone release also refines the API surface (the pre-publish design
review, `docs/project/review/senior-engineering-review-flexdoc-standalone-2026-06.md`);
these are intentional hard cuts with no compatibility aliases:

- **`TextDoc` is renamed `FlexDoc`** — the package’s single entry point, named for the
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
