"""
flexdoc is a source-grounded, layered document model for Markdown and text: parse to a
`FlexDoc`, query its structure across independent layers with `collect()`, serialize it
as a `DocGraph`, and anchor spans and edits with `SpanRef` so they survive reparse. It
is a standalone library (chopdiff builds its diff and windowed-transform layer on top
of it).

The primary entry point is exported here at the root:

```
from flexdoc import FlexDoc

doc = FlexDoc.from_text(markdown_text)
```

The full public surfaces live in the submodules:

- `flexdoc.docs` — `FlexDoc`, `Paragraph`, `Sentence`, `Section`, `Block`, `BlockType`,
  the node table, `collect()`, `DocGraph`, `SpanRef`, token diffs/mappings, and word-token
  utilities.
- `flexdoc.html` — html-in-md, html/plaintext conversion, HTML tag helpers, the content
  extractor, and timestamp extraction.
- `flexdoc.util` — read-time and token-count estimation.

Further root-level re-exports are added deliberately, not piecemeal: the root surface
definition is tracked as its own design task (beads `flexdoc-l0lc`/`flexdoc-bift`; see
`docs/project/specs/active/plan-2026-06-11-flexdoc-extraction.md`).
"""

from flexdoc.docs import FlexDoc

__all__ = ["FlexDoc"]
