---
name: inline_pathology
description: Adversarial inline constructs - an empty fenced block next to inline
  backtick runs (the cross-block pairing that once crashed node-table construction),
  unequal backtick runs, a code span with brackets, and a linked image.
---
# Inline pathology

An empty fenced block immediately followed by a paragraph mixing inline code and
backtick runs:

```python
```

Then `` ```t `` inline, a `simple` span, and code with brackets `arr[0]` and `f(x)`.

- Inline `Emphasis` text in a tight list item.

A plain [inline link](https://example.com) and an image ![alt text](https://img.example/i.png).
