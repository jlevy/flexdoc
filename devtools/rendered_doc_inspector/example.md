---
title: A rendered document
description: Hover-driven structure inspection
---

# Notes on resilient documents

A clean document should read like a document, not a parse tree. Its structure can stay
quiet until the reader needs it. Then a **paragraph**, a [source-anchored
link](https://example.com), or a `code span` can explain where it came from.

## What the parser sees

The same passage belongs to several useful layers:

- A section gives the passage a place in the document.
  - A nested item proves that structure can deepen without cluttering the page.
- A Markdown block describes how it renders.
- A sentence and its words make the prose addressable.

> Good inspection should preserve the reading experience. The source is supporting
> evidence, not the main event.

| Surface | Purpose |
| --- | --- |
| Rendered text | Read and select naturally |
| Markdown source | Verify exact syntax and offsets |

```python
doc = FlexDoc.from_text(markdown)
```

The result should feel calm before hover and precise during inspection.
