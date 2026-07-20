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
On top of the model sit portable formats: `DocGraph` serializes any slice as
language-neutral JSON, and `TextRef` makes spans, points, sections, and whole documents
durable references that resolve back to exact source.

FlexDoc is a standalone library.
[chopdiff](https://github.com/jlevy/chopdiff) builds its diff-filtering and
windowed-transform layer on top of flexdoc.

## Installation

```shell
uv add flexdoc
# or: pip install flexdoc
```

## Status

**Beta** (0.4.x). The core model is established, but the later-stage mechanisms in the
[stabilization roadmap](https://github.com/jlevy/flexdoc/blob/main/docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md)
remain open. Breaking changes before 1.0 bump the minor version, so pin a minor version.
See the [changelog](https://github.com/jlevy/flexdoc/blob/main/CHANGELOG.md).

## Usage

### Parse and Query

The primary entry point is `FlexDoc`. Parsing any input never raises: malformed
Markdown degrades deterministically and visibly. Every located unit carries an exact
`[start, end)` span into the normalized `source_text`, and `reassemble()` round-trips
the model back to normalized Markdown.

```python
from flexdoc import FlexDoc, NodeKind, TextUnit

doc = FlexDoc.from_text("# Introduction\n\nSee [docs](https://example.com/docs).\n")

# Section hierarchy with rolled-up sizes:
print(doc.section_size_tree(units=(TextUnit.words, TextUnit.sentences)))
# # Introduction  (8 words, 2 sentences)

# Sizes at every grain, including approximate LLM tokens:
print(doc.size_summary())
# 53 bytes (3 lines, 2 paras, 2 sents, 8 words, ~13 tok)

# One query primitive (collect()) spans all layers:
link = doc.collect(kinds={NodeKind.link})[0]
print(link.attrs["url"], link.source_span)
# https://example.com/docs (20, 52)
```

FlexDoc delegates Markdown parsing to [marko](https://github.com/frostming/marko)
(CommonMark with GFM tables and footnotes) via
[flowmark](https://github.com/jlevy/flowmark), and adds sentence segmentation, the
section hierarchy, the flat node table, offset-grounded queries, references,
serialization, and span anchoring on top.

### Reference and Annotate: TextRef

Continuing the example, any public value maps to a
[`TextRef`](https://github.com/jlevy/flexdoc/blob/main/docs/flexdoc-spec.md#11-textref-spanref-and-annotations):
a portable reference carrying quote evidence and a source hash, with canonical JSON and
a reversible `textref:0.1` URI projection.

```python
refs = doc.references(document="guide.md")
ref = refs.for_target(link)

print(ref.to_uri())
# textref:0.1?doc=guide.md&hash=sha256%3A0e91...0f86&type=span
#     &exact=%5Bdocs%5D%28https%3A%2F%2Fexample.com%2Fdocs%29&prefix=...&start=20

res = refs.resolve(ref)
print(res.resolved, res.method.value, (res.span.start, res.span.end))
# True source_position (20, 52)
```

Annotations attach consumer-owned content to TextRef targets, and `AnnotationSet` is
their one-document JSON/YAML sidecar form:

```python
from flexdoc import AnnotationSet, TextAnnotation, TextBody

note = TextAnnotation(id="n1", target=ref, motivations=["commenting"],
                      body=TextBody(type="text", value="Check this link."))
sidecar = AnnotationSet.from_annotations([note])

print(sidecar.to_yaml())
# format: text-annotations/0.1
# document: guide.md
# source_hash: sha256:0e91...0f86
# annotations:
# - id: n1
#   ...
```

### Serialize: DocGraph

[`DocGraph`](https://github.com/jlevy/flexdoc/blob/main/docs/flexdoc-spec.md#10-docgraph-the-serialized-projection)
is the language-neutral serialized projection: one source-anchored object carrying
document identity, a source hash shared with TextRef, the node table, derived views,
and (optionally) an embedded annotation sidecar. JSON is the wire form; YAML is the
human and golden-test form.

```python
graph = doc.graph(document="guide.md", annotations=sidecar)

print(graph.to_yaml())
# schema: DocGraph/v0.2
# source:
#   format: markdown
#   offset_unit: unicode_code_points
#   document: guide.md
#   source_hash: sha256:0e91...0f86
# nodes:
# - id: n0001
#   kind: heading
#   layer: markdown
#   source_span:
#     start: 0
#     end: 14
#   attrs:
#     level: 1
# ... (more nodes, then views and the embedded annotations)
```

### Word and Token Metrics

`TextUnit.words` is a logical-word measure: it matches a whitespace count for ordinary
non-wide prose averaging 3–6 characters per word, but normalizes wide/fullwidth scripts,
long identifiers and URLs, short-token sequences, and punctuation-dense code or
Markdown. Use `TextUnit.raw_words` for a literal whitespace-delimited count. See the
[logical-word definition and validation](https://gist.github.com/jlevy/0d6d87885f6d85f31440e58b8cfce663)
for the rationale, reference algorithm, and multilingual examples.

### Module Map

The full public surfaces live in the submodules:

- `flexdoc.docs`: `FlexDoc`, `Paragraph`, `Sentence`, `Section`, `Block`, `BlockType`,
  the node table, `collect()`, `DocGraph`, `TextRef`, annotation values, `SpanRef`, and
  source-linked render/report helpers.
- `flexdoc.docs.wordtoks`, `flexdoc.docs.search_tokens`,
  `flexdoc.docs.token_diffs`, and `flexdoc.docs.token_mapping`: lower-level token,
  search, diff, and mapping utilities that are not promoted by `flexdoc.docs`.
- `flexdoc.html`: html-in-md, html/plaintext conversion, HTML tag helpers, the content
  extractor, and timestamp extraction.
- `flexdoc.util`: raw and cross-language logical word counts, read-time estimation, and
  approximate token-count estimation.

### Worked Examples

See [usage.md](https://github.com/jlevy/flexdoc/blob/main/docs/usage.md) for the main
workflows. Each worked example is a runnable script (run with
`uv run python examples/<name>.py` from a checkout) demonstrating one workflow
end to end:

- [`doc_structure.py`](https://github.com/jlevy/flexdoc/blob/main/examples/doc_structure.py)
  covers section hierarchy, size rollups, offset lookups, and the block tree.
- [`normalized_form.py`](https://github.com/jlevy/flexdoc/blob/main/examples/normalized_form.py)
  covers block-type tallies, list-density invariance, and per-section links.
- [`backfill_timestamps.py`](https://github.com/jlevy/flexdoc/blob/main/examples/backfill_timestamps.py)
  aligns an edited transcript to its timestamped source via token mapping.
- [`textref_workflows.py`](https://github.com/jlevy/flexdoc/blob/main/examples/textref_workflows.py)
  composes extraction provenance, context retrieval, citations, annotations, and edit
  targets.

## Design

The design of record is
[flexdoc-spec.md](https://github.com/jlevy/flexdoc/blob/main/docs/flexdoc-spec.md),
which motivates each decision and defines the invariants the tests pin. The ideas that
carry the model:

- **One coordinate space.** Every layer indexes the same retained, normalized source
  string with `[start, end)` Unicode code-point offsets, so cross-layer questions reduce
  to offset queries
  ([spec §2](https://github.com/jlevy/flexdoc/blob/main/docs/flexdoc-spec.md#2-principles-and-goals)).
- **Layers are independent parses.** Markdown structure, prose sentences, and the
  heading hierarchy are separate projections of the same text; no single tree has to be
  authoritative
  ([spec §4](https://github.com/jlevy/flexdoc/blob/main/docs/flexdoc-spec.md#4-core-types-nodes-and-offsets)).
- **Parsing never raises.** Malformed Markdown degrades deterministically and visibly,
  pinned by the golden-test corpus
  ([spec §13](https://github.com/jlevy/flexdoc/blob/main/docs/flexdoc-spec.md#13-invariants-and-non-goals)).
- **References carry evidence, and resolution never guesses.** Positions are trusted
  only under a matched source hash; quotes and context corroborate; a duplicated quote
  resolves to a typed ambiguous outcome, never a silent first match
  ([spec §11](https://github.com/jlevy/flexdoc/blob/main/docs/flexdoc-spec.md#11-textref-spanref-and-annotations)).
  `SpanRef` is the lightweight quote anchor underneath.
- **Serialized contracts are strict and versioned.** `DocGraph/v0.2` and `textref/0.1`
  reject unknown fields, and both ship committed JSON Schemas:
  [doc_graph_schema.json](https://github.com/jlevy/flexdoc/blob/main/src/flexdoc/docs/doc_graph_schema.json)
  and
  [text_ref_schema.json](https://github.com/jlevy/flexdoc/blob/main/src/flexdoc/docs/text_ref_schema.json)
  ([spec §10](https://github.com/jlevy/flexdoc/blob/main/docs/flexdoc-spec.md#10-docgraph-the-serialized-projection)).

## Project Docs

For users:

- Design of record (the full spec):
  [flexdoc-spec.md](https://github.com/jlevy/flexdoc/blob/main/docs/flexdoc-spec.md).
- Usage guide: [usage.md](https://github.com/jlevy/flexdoc/blob/main/docs/usage.md).
- Installing uv and Python:
  [installation.md](https://github.com/jlevy/flexdoc/blob/main/docs/installation.md).

For contributors:

- Development workflows:
  [development.md](https://github.com/jlevy/flexdoc/blob/main/docs/development.md).
- Publishing to PyPI:
  [publishing.md](https://github.com/jlevy/flexdoc/blob/main/docs/publishing.md).
- Dependency policy:
  [SUPPLY-CHAIN-SECURITY.md](https://github.com/jlevy/flexdoc/blob/main/SUPPLY-CHAIN-SECURITY.md).
- Design history and plans (active and done):
  [docs/project/specs/](https://github.com/jlevy/flexdoc/tree/main/docs/project/specs).

* * *

*This project was built from
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
