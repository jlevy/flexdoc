# Usage Guide

`FlexDoc` is the package entry point.
It parses Markdown into one source-grounded document model, then exposes several
projections over the same character offsets.

```python
from flexdoc import FlexDoc, TextUnit

doc = FlexDoc.from_text("# Title\n\nSee [docs](https://example.com/docs).\n")
```

## Main Workflows

### Analyze Prose

Use `paragraphs`, `sentences`, and size helpers when the task is about prose rather than
Markdown syntax.

```python
for paragraph in doc.paragraphs:
    print(paragraph.original_text, paragraph.size(TextUnit.words))

print(doc.size_summary())
```

`TextUnit.words` is the normal human-readable size metric and always means logical
words. For non-wide text, it equals `TextUnit.raw_words` when the average
whitespace-delimited word has 3–6 non-whitespace characters. Longer averages increase
the logical count; shorter averages decrease it. Wide/fullwidth characters contribute
0.5 word each, making unspaced CJK text measurable. Long identifiers, URLs, Markdown
syntax, code, and other non-textual or symbolic runs can therefore differ from an
ordinary expected word count.

Both measures use an HTML plain-text projection, so non-visible HTML markup is excluded.
Use `TextUnit.raw_words` when a literal whitespace-delimited count of that projection is
required. Document and section word totals are computed over the full aggregate before
rounding, so they can differ from the sum of independently rounded sentence counts.

Offsets in paragraphs and sentences point into `doc.source_text`. If the source starts
with YAML frontmatter, frontmatter is exposed as `doc.frontmatter` and excluded from the
prose view. Opening and closing `---` delimiters may have trailing spaces or tabs but
must not have leading whitespace.

### Extract Prose Text

Use `prose_text()` for the readable prose of the document with non-prose blocks (code,
HTML, frontmatter, reference definitions) and inline noise (code spans, HTML tags,
footnote references) removed; links and images are reduced to their text/alt.
Emphasis markers (`**`, `*`) are preserved.

```python
prose = doc.prose_text()
prose_with_tables = doc.prose_text(include_tables=True)
```

This is the projection to use for editorial linting, prose metrics, and preparing clean
text for LLM prompts or embeddings.

### Inspect Markdown Structure

Use `blocks()` for the recursive Markdown block tree and `base_blocks()` for the flat
ordered partition of content blocks.

```python
for block in doc.blocks():
    print(block.type, block.span)

for base in doc.base_blocks():
    print(base.depth, base.block.type, base.block.span)
```

`blocks()` is the structural query view.
`base_blocks()` is the sequential content partition used when you need document-order
coverage.

### Work With Sections and Links

Use `sections()` for the heading hierarchy.
Each `Section` can report its own content, subtree content, sizes, and links.

```python
for section in doc.sections():
    print(section.title, section.size(TextUnit.words))
    for link in section.links():
        print(link.text, link.url)
```

`doc.links()` resolves inline links, autolinks, bare URLs, and reference-style links
within the content body.
Leading YAML frontmatter is non-content, so links and reference definitions there do not
affect `doc.links()`.

### Query the Normalized Node Table

Use `node_table()` or `collect()` when a workflow needs one id space across Markdown,
document, and textual layers.

```python
from flexdoc import Layer, NodeKind

table = doc.node_table()
headings = doc.collect(kinds={NodeKind.heading}, layer={Layer.markdown})
links = doc.collect(kinds={NodeKind.link})
```

The node table is a normalized projection, not a replacement for the source text.
Its nodes carry source spans where they can be located.

### Serialize a DocGraph

Use `graph()` when a UI or service boundary needs a JSON-safe document projection.
The textual layer adds ordered paragraph and sentence views, both as node ids over the
same source offsets as Markdown blocks and document sections.

```python
from flexdoc import Detail, Layer

graph = doc.graph(
    include={Layer.markdown, Layer.document, Layer.textual},
    detail={Detail.text, Detail.inline},
)

paragraph_nodes = [node for node in graph.nodes if node.id in graph.views.paragraphs]
sentence_nodes = [node for node in graph.nodes if node.id in graph.views.sentences]
```

### Persist and Resolve Spans

Use `SpanRef` when a tool needs to persist a source reference and re-resolve it after a
reparse. A `SpanRef` carries a text quote (the durable anchor) plus offsets (a
recomputable hint): `to_persisted()` drops the offsets, keeping the quote, and
`SpanRef.resolve()` re-locates the quote in the (possibly changed) source, returning
`None` if the quote is gone or ambiguous.

```python
from flexdoc import SpanRef

link_nodes = doc.collect(kinds={NodeKind.link})
ref = SpanRef.from_node(link_nodes[0], doc.source_text)
print(ref.to_persisted().resolve(doc.source_text))
```

### Transform Text

Editing methods build transformed output through `reassemble()`. Source offsets still
refer to the original parsed text.
Reparse transformed output before analyzing its new structure.

```python
doc.replace_str("docs", "guide")
updated = FlexDoc.from_text(doc.reassemble())
```

### Import Lower-Level Token and Diff Utilities Explicitly

`flexdoc.docs` promotes the document model.
Word-token, token-diff, mapping, and search utilities remain available from their owning
modules for lower-level pipelines:

```python
from flexdoc.docs.search_tokens import search_tokens
from flexdoc.docs.token_diffs import TokenDiff, diff_wordtoks
from flexdoc.docs.token_mapping import TokenMapping
from flexdoc.docs.wordtoks import PARA_BR_TOK, wordtokenize
```

These names are not re-exported from `flexdoc.docs`.

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
