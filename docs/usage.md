# Usage Guide

`FlexDoc` is the package entry point. It parses Markdown into one source-grounded
document model, then exposes several projections over the same character offsets.

```python
from flexdoc import FlexDoc
from flexdoc.docs import TextUnit

doc = FlexDoc.from_text("# Title\n\nSee [docs](https://example.com/docs).\n")
```

## Main Workflows

### Analyze Prose

Use `paragraphs`, `sentences`, and size helpers when the task is about prose rather
than Markdown syntax.

```python
for paragraph in doc.paragraphs:
    print(paragraph.original_text, paragraph.size(TextUnit.words))

print(doc.size_summary())
```

Offsets in paragraphs and sentences point into `doc.source_text`. If the source starts
with YAML frontmatter, frontmatter is exposed as `doc.frontmatter` and excluded from the
prose view.

### Inspect Markdown Structure

Use `blocks()` for the recursive Markdown block tree and `base_blocks()` for the flat
ordered partition of content blocks.

```python
for block in doc.blocks():
    print(block.type, block.span)

for base in doc.base_blocks():
    print(base.depth, base.block.type, base.block.span)
```

`blocks()` is the structural query view. `base_blocks()` is the sequential content
partition used when you need document-order coverage.

### Work With Sections and Links

Use `sections()` for the heading hierarchy. Each `Section` can report its own content,
subtree content, sizes, and links.

```python
for section in doc.sections():
    print(section.title, section.size(TextUnit.words))
    for link in section.links():
        print(link.text, link.url)
```

`doc.links()` resolves inline links, autolinks, bare URLs, and reference-style links
within the content body. Leading YAML frontmatter is non-content, so links and reference
definitions there do not affect `doc.links()`.

### Query the Normalized Node Table

Use `node_table()` or `collect()` when a workflow needs one id space across Markdown,
document, and textual layers.

```python
from flexdoc.docs import Layer, NodeKind

table = doc.node_table()
headings = doc.collect(kinds={NodeKind.heading}, layer={Layer.markdown})
links = doc.collect(kinds={NodeKind.link})
```

The node table is a normalized projection, not a replacement for the source text. Its
nodes carry source spans where they can be located.

### Persist and Resolve Spans

Use `SpanRef` when a tool needs to persist a source reference and re-resolve it after a
reparse.

```python
from flexdoc.docs import SpanRef, resolve

node = next(n for n in doc.node_table().nodes.values() if n.kind == NodeKind.link)
ref = SpanRef.from_node(node, doc.source_text)
print(resolve(ref.to_persisted(), doc.source_text))
```

### Transform Text

Editing methods build transformed output through `reassemble()`. Source offsets still
refer to the original parsed text. Reparse transformed output before analyzing its new
structure.

```python
doc.replace_str("docs", "guide")
updated = FlexDoc.from_text(doc.reassemble())
```

## Examples

Run the worked examples from a repository checkout:

```shell
uv run python examples/doc_structure.py
uv run python examples/normalized_form.py
uv run python examples/backfill_timestamps.py
```

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
