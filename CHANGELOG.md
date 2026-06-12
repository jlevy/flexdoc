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

  The import roots are `flexdoc.docs`, `flexdoc.html`, and `flexdoc.util`. The public
  behavior is unchanged from the `flexdoc.*` modules that previously shipped inside the
  chopdiff wheel; this release packages them independently. See
  `docs/project/specs/active/plan-2026-06-11-flexdoc-extraction.md`.
