"""
flexdoc is a source-grounded, layered document model for Markdown and text: parse to a
`TextDoc`/`DocGraph`, query structure across layers with `collect()`, and anchor spans
and edits with `SpanRef`. It is a standalone library (chopdiff builds its diff and
windowed-transform layer on top of it). It has no root-level public API by design; import
from the submodules, which carry the explicit public surfaces:

- `flexdoc.docs` — `TextDoc`, `Paragraph`, `Sentence`, `Section`, `Block`, `BlockType`,
  the node table, `collect()`, `DocGraph`, `SpanRef`, token diffs/mappings, and word-token
  utilities.
- `flexdoc.html` — html-in-md, html/plaintext conversion, HTML tag helpers, the content
  extractor, and timestamp extraction.
- `flexdoc.util` — read-time and token-count estimation.

Root-level convenience re-exports may be added once the public-API surface (see
`docs/project/specs/active/plan-2026-05-29-unified-document-model.md`) is settled, so the
top-level API is designed once rather than piecemeal.
"""
