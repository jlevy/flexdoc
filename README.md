# FlexDoc

[![PyPI version](https://img.shields.io/pypi/v/flexdoc)](https://pypi.org/project/flexdoc/)
[![CI](https://github.com/jlevy/flexdoc/actions/workflows/ci.yml/badge.svg)](https://github.com/jlevy/flexdoc/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/jlevy/flexdoc/blob/main/LICENSE)
[![Python versions](https://img.shields.io/pypi/pyversions/flexdoc)](https://pypi.org/project/flexdoc/)

A Markdown parser gives you a block AST but no sentences, sizes, or exact source
offsets. An NLP toolkit gives you sentences but no Markdown structure.
If you need to know which sentence is in which section, how many words (or LLM tokens) a
section holds, or exactly where a link sits in the original text, you end up gluing
tools together; the glue breaks on the first edit.

FlexDoc builds a single source-grounded model and exposes its structure as layers over
one shared coordinate space: exact `[start, end)` offsets into one retained, normalized
source string. The **Markdown layer** (blocks, inline elements, typed attributes), the
**textual layer** (paragraphs, sentences, word tokens), and the **document layer**
(heading hierarchy, table of contents) are independent parses of the same text, so
cross-cutting questions are simple offset queries.
One query primitive (`collect()`) spans all layers; **`DocGraph`** serializes any slice
as language-neutral JSON; **`SpanRef`** anchors spans by quoted text so references
survive edits and reparses.

FlexDoc is a standalone library.
[chopdiff](https://github.com/jlevy/chopdiff) builds its diff-filtering and
windowed-transform layer on top of flexdoc.

## Installation

```shell
uv add flexdoc
# or: pip install flexdoc
```

## Status

**Beta** (0.2.x). The core model is established, but the API decisions in the
[stabilization roadmap](https://github.com/jlevy/flexdoc/blob/main/docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md)
remain open. Breaking changes before 1.0 bump the minor version, so pin a minor version.
See the [changelog](https://github.com/jlevy/flexdoc/blob/main/CHANGELOG.md).

## Usage

The primary entry point is `FlexDoc`:

```python
from flexdoc import FlexDoc, NodeKind, TextUnit

markdown_text = "# Introduction\n\nSee [docs](https://example.com/docs).\n"
doc = FlexDoc.from_text(markdown_text)

# Section hierarchy with rolled-up sizes:
print(doc.section_size_tree(units=(TextUnit.words, TextUnit.sentences)))
# # Introduction  (4 words, 2 sentences)

# Sizes at every grain, including approximate LLM tokens:
print(doc.size_summary())
# 53 bytes (3 lines, 2 paras, 2 sents, 4 words, ~14 tok)

# One query primitive across all layers:
link = doc.collect(kinds={NodeKind.link})[0]
print(link.attrs["url"], link.source_span)
# https://example.com/docs (20, 52)

# Round-trips back to normalized Markdown:
print(doc.reassemble())
```

Every located source-backed unit carries an exact `[start, end)` span into normalized
`source_text`; paragraphs and sentences also expose that slice as `original_text`. Some
parser-derived identities can be unlocatable and therefore carry `span=None`.

FlexDoc delegates Markdown parsing to [marko](https://github.com/frostming/marko)
(CommonMark with GFM tables and footnotes) via
[flowmark](https://github.com/jlevy/flowmark), and adds sentence segmentation, the
section hierarchy, the flat node table, offset-grounded queries, serialization, and span
anchoring on top. Parsing any input never raises: malformed Markdown degrades
deterministically and visibly (see the
[spec](https://github.com/jlevy/flexdoc/blob/main/docs/flexdoc-spec.md) and the
golden-test corpus that pins this behavior).

The full public surfaces live in the submodules:

- `flexdoc.docs`: `FlexDoc`, `Paragraph`, `Sentence`, `Section`, `Block`, `BlockType`,
  the node table, `collect()`, `DocGraph`, `SpanRef`, token diffs/mappings, and
  word-token utilities.
- `flexdoc.html`: html-in-md, html/plaintext conversion, HTML tag helpers, the content
  extractor, and timestamp extraction.
- `flexdoc.util`: read-time and token-count estimation.

See [usage.md](https://github.com/jlevy/flexdoc/blob/main/docs/usage.md) for the main
workflows, and the worked examples (run with `uv run python examples/<name>.py` from a
checkout):

- [`doc_structure.py`](https://github.com/jlevy/flexdoc/blob/main/examples/doc_structure.py)
  covers section hierarchy, size rollups, offset lookups, and the block tree.
- [`normalized_form.py`](https://github.com/jlevy/flexdoc/blob/main/examples/normalized_form.py)
  covers block-type tallies, list-density invariance, and per-section links.
- [`backfill_timestamps.py`](https://github.com/jlevy/flexdoc/blob/main/examples/backfill_timestamps.py)
  aligns an edited transcript to its timestamped source via token mapping.

## Project Docs

For users:

- Design of record (the full spec):
  [flexdoc-spec.md](https://github.com/jlevy/flexdoc/blob/main/docs/flexdoc-spec.md).
- Installing uv and Python:
  [installation.md](https://github.com/jlevy/flexdoc/blob/main/docs/installation.md).

For contributors:

- Development workflows:
  [development.md](https://github.com/jlevy/flexdoc/blob/main/docs/development.md).
- Publishing to PyPI:
  [publishing.md](https://github.com/jlevy/flexdoc/blob/main/docs/publishing.md).
- Dependency policy:
  [SUPPLY-CHAIN-SECURITY.md](https://github.com/jlevy/flexdoc/blob/main/SUPPLY-CHAIN-SECURITY.md).
- Design history and plans:
  [docs/project/specs/active/](https://github.com/jlevy/flexdoc/tree/main/docs/project/specs/active).

* * *

*This project was built from
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
