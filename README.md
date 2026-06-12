# flexdoc

flexdoc is a document model for powerful text parsing and processing in Markdown: a
source-grounded, layered model of Markdown and text. It parses a document into a
`TextDoc`/`DocGraph`, lets you query its structure across independent layers with a
single `collect()` primitive, and anchors spans and edits with `SpanRef` so they survive
a reparse.

The aim is fine-grained understanding of a complex Markdown document along several
independent axes at once — its **Markdown syntax** (blocks, inline elements, exact spans,
typed attributes), its **grammar and language** (paragraphs, sentences, tokens), and
other structures layered onto the same text — over one shared coordinate space.

flexdoc is a standalone library. [chopdiff](https://github.com/jlevy/chopdiff) builds its
diff-filtering and windowed-transform layer on top of flexdoc.

## Installation

```shell
uv add flexdoc
# or: pip install flexdoc
```

## Usage

flexdoc has no root-level public API by design; import from the submodules, which carry
the explicit public surfaces:

- `flexdoc.docs` — `TextDoc`, `Paragraph`, `Sentence`, `Section`, `Block`, `BlockType`,
  the node table, `collect()`, `DocGraph`, `SpanRef`, token diffs/mappings, and
  word-token utilities.
- `flexdoc.html` — html-in-md, html/plaintext conversion, HTML tag helpers, the content
  extractor, and timestamp extraction.
- `flexdoc.util` — read-time and token-count estimation.

```python
from flexdoc.docs import TextDoc

doc = TextDoc.from_text("# Title\n\nHello world. This is a second sentence.\n")

# Round-trips back to normalized Markdown.
print(doc.reassemble())

# Human-readable size stats (paragraphs, sentences, words, ...).
print(doc.size_summary())
```

See [examples/](examples/) for worked scripts (run any with `uv run examples/<name>.py`).

## Project Docs

- Design of record: [docs/textdoc-spec.md](docs/textdoc-spec.md).
- The extraction program and the model's design history:
  [docs/project/specs/active/](docs/project/specs/active/).
- For how to install uv and Python, see [installation.md](docs/installation.md).
- For development workflows, see [development.md](docs/development.md).
- For publishing to PyPI, see [publishing.md](docs/publishing.md).
- Dependency policy: [SUPPLY-CHAIN-SECURITY.md](SUPPLY-CHAIN-SECURITY.md).

* * *

*This project was built from
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
