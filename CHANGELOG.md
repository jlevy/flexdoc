# Changelog

All notable changes to flexdoc are documented here.
This project uses [semantic versioning](https://semver.org/); while pre-1.0, breaking
changes bump the **minor** version (see `docs/publishing.md`).

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
