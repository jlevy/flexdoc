"""
flexdoc is a source-grounded, layered document model for Markdown and text: parse to a
`FlexDoc`, query its structure across independent layers with `collect()`, serialize it
as a `DocGraph`, and anchor spans and edits with `SpanRef` so they survive reparse. It
is a standalone library (chopdiff builds its diff and windowed-transform layer on top
of it).

The root exports the working set for typical use — the entry point, the serialization
contract, the reference type, and the enums nearly every query or measurement needs:

```
from flexdoc import FlexDoc, NodeKind, TextUnit

doc = FlexDoc.from_text(markdown_text)
links = doc.collect(kinds={NodeKind.link}, recursive=True)
words = doc.size(TextUnit.words)
```

The full public surfaces live in the submodules:

- `flexdoc.docs` — `FlexDoc`, `Paragraph`, `Sentence`, `Section`, `Block`, `BlockType`,
  the node table, `collect()`, `DocGraph`, `SpanRef` and its resolvers, render helpers
  for source-linked HTML, token diffs/mappings, and word-token utilities.
- `flexdoc.html` — html-in-md, html/plaintext conversion, HTML tag helpers, the content
  extractor, and timestamp extraction.
- `flexdoc.util` — read-time and token-count estimation.

Unit types (`Paragraph`, `Sentence`, `Section`, `Block`, `Node`) are reached from a
parsed `FlexDoc` rather than imported, so they stay in `flexdoc.docs`, as do functions
whose bare names need module context (e.g. `resolve`). Root additions are deliberate;
`tests/test_root_api.py` pins the exact surface.
"""

from flexdoc.docs import (
    BlockType,
    Detail,
    DocGraph,
    FlexDoc,
    Layer,
    NodeKind,
    SpanRef,
    TextUnit,
)

__all__ = [
    "BlockType",
    "Detail",
    "DocGraph",
    "FlexDoc",
    "Layer",
    "NodeKind",
    "SpanRef",
    "TextUnit",
]
