# Draft Post: A Document Model Where the Text Stays Canonical

**Status:** Draft for review, 2026-07. Not published.
A concise introduction post for flexdoc, aimed at engineers building document-processing
and AI/LLM workflows.
Working titles below; pick one, cut the rest.

- *A document model where the text stays canonical*
- *flexdoc: source-grounded, layered structure for Markdown*
- *Stop choosing between a Markdown AST and an NLP pipeline*

* * *

Most document models make the structure canonical: a DOM, an mdast tree, a ProseMirror
or Notion block hierarchy.
The text lives *inside* the tree, and querying, editing, and annotation happen in the
tree’s terms. That works well for editors.
It works badly for the workflows that now dominate document processing: analyzing,
chunking, quoting, diffing, and annotating text with LLMs, where the natural currency is
*the text itself*: quotes, spans, and token budgets, not node ids in someone’s tree.

[flexdoc](https://github.com/jlevy/flexdoc) inverts the usual arrangement.
The source text is the one canonical thing.
Everything else, including Markdown block structure, inline elements, sentences,
paragraphs, and the heading hierarchy, is a derived projection over one shared
coordinate space: exact `[start, end)` offsets into one immutable string.

```python
from flexdoc import FlexDoc, NodeKind, TextUnit

doc = FlexDoc.from_text(markdown_text)

doc.sections()          # heading hierarchy, each with sizes and links
doc.blocks()            # recursive Markdown block tree with exact source spans
doc.paragraphs          # blank-line editing view: paragraphs, sentences, words
doc.collect(kinds={NodeKind.link})   # one query primitive across all layers
doc.size(TextUnit.tokens)            # approximate LLM tokens, or words/sentences/...
```

## One Text, Several Parses

The core idea is **layered parsing**. The same source string is parsed along independent
dimensions:

- a **markdown** layer: the block and inline structure (headings, lists, tables, code,
  links), with every element carrying its exact source span;
- a **textual** layer: paragraphs, sentences, and word tokens, the units prose editing
  and diffing actually operate on;
- a **document** layer: the heading/section hierarchy and table of contents;
- a specified, future **synthetic** layer for marker-tag regions that tools or authors
  embed in the text.

Layers never point at each other with stored edges.
“Which section contains this link” or “which blocks are inside this region” are
*offset-containment queries* over the shared coordinate space.
That is what lets cross-cutting structures coexist without contradiction: a section
spans sibling blocks and is not a subtree of the block tree; an annotation can target
half a sentence; a marked region can open mid-block.
None of them fight over one tree.

A Markdown parser gives you an AST but no sentences, sizes, or exact source mapping.
An NLP toolkit gives you sentences but no Markdown structure.
FlexDoc provides both over one retained source string.
Every located source-backed unit has an exact span, and paragraphs and sentences also
expose the slice as `original_text`:

```python
source_text[paragraph.span[0] : paragraph.span[1]] == paragraph.original_text
```

## Why This Shape Fits AI Workflows

**Grounded citation.** When an LLM quotes a document, the quote *is* the anchor.
FlexDoc’s `SpanRef` is a quoted span (`exact` plus `prefix`/`suffix` context) with
offsets as a recomputable hint.
Its quote fields mirror the
[W3C Text Quote Selector](https://www.w3.org/TR/annotation-model/#text-quote-selector),
and its shareable links follow
[URL Fragment Text Directives](https://wicg.github.io/scroll-to-text-fragment/). A
model-produced quote resolves to an exact span; a span converts to a Chrome-style
`#:~:text=` link when the quote is visible prose.
Markdown-bearing source spans need a rendered-text projection before a browser can match
them.
Refs with captured context survive reparsing and many surrounding edits; missing or
ambiguous quotes resolve to `None`.

**Annotation and commenting.** Comments, suggestions, and reviews are stand-off records
targeting spans, the same kind of thing as the parsed structure itself but in another
layer over the same offsets.
Nothing is inserted into the text; the document round-trips untouched.

**Chunking and budgeting.** Every unit, from document and section to block, paragraph,
and sentence, reports its size in words, sentences, paragraphs, or approximate LLM
tokens, computed on demand.
Windowing a long document into context-sized pieces along *structural* boundaries
(sections, then blocks, then sentences) is a query, not a preprocessing pipeline.

**Structure for prompts, JSON for tools.** The whole parse (or any slice of it)
serializes as `DocGraph`, a language-neutral JSON contract: a flat node table with ids,
kinds, layers, spans, and typed attributes.
One schema serves frontends, cross-language clients, and tool-calling LLMs.

**Editing without drift.** Edits go through the editing view, and `reassemble()`
produces clean normalized Markdown.
Reparsing that output establishes the next source and coordinate space; cached structure
is never patched incrementally.

## What It Is and Isn’t

flexdoc is a Python library (`uv add flexdoc`), extracted from and used by
[chopdiff](https://github.com/jlevy/chopdiff), which builds word-level diff filtering
and windowed LLM transforms on top of it.
It has a
[full design spec](https://github.com/jlevy/flexdoc/blob/main/docs/flexdoc-spec.md), a
golden-test corpus pinning its behavior on malformed input (parsing never throws;
degradation is deterministic and visible), and deterministic node ids designed so future
cross-language ports (TypeScript, Rust) can implement the same `DocGraph` contract.

It is not a renderer, not an editor, and not another Markdown AST. It is the layer those
tools share: one source of truth for *where everything is* in a document.

It is early (0.2.x): the annotation layer and synthetic-tag layer are specified but not
yet built, and the API may still move before 1.0. If you are building document analysis,
review, or LLM feedback tooling and want a model where the text stays the text, take a
look.

* * *

**Editor notes (cut before publishing):**

- Candidate lead example to add: a 10-line “LLM reviews a doc and attaches comments”
  round trip (prompt → quote → `SpanRef` → resolved span → text-fragment link) once the
  annotation container type lands; today the same flow works with `SpanRef` alone.
- Possible comparison table (mdast / pandoc / tree-sitter / spaCy vs flexdoc) if the
  post runs long; prose comparison kept short here on purpose.
- Link targets to verify at publish time: PyPI page, spec anchor stability.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
