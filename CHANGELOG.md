# Changelog

All notable changes to flexdoc are documented here.
This project uses [semantic versioning](https://semver.org/); while pre-1.0, breaking
changes bump the **minor** version (see `docs/publishing.md`).

## Unreleased

### Added

- **Initial flexdoc package**, extracted from
  [chopdiff](https://github.com/jlevy/chopdiff) as its own standalone distribution. This
  is the document/markdown layer — `TextDoc`, paragraphs/sentences, the block tree and
  block types, sections, the node table, `collect()`, `DocGraph`, `SpanRef`, token
  diffs/mappings, word tokenization, html-in-md, and read-time/token estimation — with no
  dependency on chopdiff's diff and windowed-transform machinery.

  The import roots are `flexdoc.docs`, `flexdoc.html`, and `flexdoc.util`. Parse
  behavior is unchanged from the `flexdoc.*` modules that previously shipped inside the
  chopdiff wheel; this release packages them independently. See
  `docs/project/specs/active/plan-2026-06-11-flexdoc-extraction.md`.

### Changed (relative to the modules as shipped in chopdiff)

The first standalone release also refines the API surface (the pre-publish design
review, `docs/project/review/senior-engineering-review-flexdoc-standalone-2026-06.md`);
these are intentional hard cuts with no compatibility aliases:

- **`collect()` is fully keyword-only and the deprecated aliases are gone**: use
  `subtree_of=` (was `scope=`, previously also positional) and `within=` (was
  `contains=`).
- **Editing-view methods are named in paragraph terms**, so "block" always means the
  structural layer: `TextDoc.block_at_offset` → `paragraph_at_offset`,
  `TextDoc.iter_blocks` → `iter_paragraphs`, `Section.own_blocks`/`subtree_blocks` →
  `own_paragraphs`/`subtree_paragraphs`.
- **The export surface is settled**: `flexdoc.docs` now exports
  `CodeInfo`/`TableInfo`/`ListInfo`, `resolve`/`resolve_and_update`,
  `parse_blocks`/`walk_blocks`/`block_type_for`, and `DEFAULT_INCLUDE`;
  `flexdoc.html` exports `html_p`, `html_tag`, `escape_attribute`, `tag_wrapper`, and
  `identity_wrapper`. Link extraction is public as
  `flexdoc.docs.links.block_links`.
- **`Node.attrs` values are JSON-typed** (`AttrValue`), validated at `DocGraph`
  serialization, and node-id assignment order is pinned and tested for cross-language
  ports; layer nesting guarantees (`LAYER_NESTING`) are enforced at node-table build.
- Internally, `text_doc.py` was split into `paragraphs.py`, `links.py`, and
  `sections.py` (package imports from `flexdoc.docs` are unaffected), and `sections()`
  is now cached like the other derived views.
