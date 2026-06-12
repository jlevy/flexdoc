# FlexDoc and DocGraph: Design Specification

**Status:** Specifies the document model in the `flexdoc` package: the `FlexDoc` Python
core and the `DocGraph` serialized projection.
Design decisions are recorded in this document; §14 states what is implemented versus
specified but not yet built.
Dated planning documents under `docs/project/specs/` track work toward this spec and
reference it; this spec does not depend on them.

## 1. Purpose

The document model consolidates, in one source-anchored structure, what a document
analysis or editing task normally needs from separate tools, and anchors every piece
back to the source by exact character offset:

- **Markdown block structure:** headings, paragraphs, lists/list items, tables, code,
  blockquotes, HTML, footnotes, thematic breaks.
- **Markdown inline structure:** links, code spans, inline HTML.
- **Language structure:** paragraphs, sentences, and words, with the exact spacing
  between them.
- **Document structure:** heading hierarchy and table of contents.
- **Document sizes at every grain:** bytes, characters, lines, words, sentences,
  paragraphs — and **approximate LLM token estimates** — all derived on demand, never
  stored. Sizing matters because the model’s main consumers window, chunk, and budget
  documents for LLM processing.

A Markdown parser gives you a block/inline AST but no sentences, sizes, or section
rollups. An NLP toolkit gives sentences but no Markdown structure and no exact source
mapping. This model is both, anchored to one retained source string.

Two surfaces, one design:

- **`FlexDoc`** is the **Python core:** the in-process object for parsing, analysis,
  rollups, transforms, and editable reassembly.
- **`DocGraph`** is the **serialized, language-neutral projection** of the same content:
  a JSON contract for frontends, cross-language clients, and annotations.
  It is derived from `FlexDoc`, not a competing model.

### Terminology

Terms used throughout; each is detailed in the section noted.

- **Source text** — the single immutable input string a `FlexDoc` retains.
  Everything else is derived from it (§4.1).
- **Offset / span** — a position, or `[start, end)` half-open range, in the source text,
  measured in **Unicode code points** (§4.1).
- **Layer** — one independent parse dimension over the same source: `textual`,
  `markdown`, `document`, `synthetic` (§3).
- **Node / node table / node kind** — the id-addressed record of one parsed element; the
  flat table of all of them across layers; and the element’s type tag (heading,
  paragraph, link, section, ...) (§4.3).
- **Block** — a Markdown block-level element.
  §6 disambiguates the three precise senses: *block element* (the CommonMark class),
  *block node* (a node in the recursive structural tree), and *base block* (a unit of
  the flat sequential partition).
- **Paragraph / sentence (editing view)** — the blank-line-delimited units and their
  sentences; the mutable view edits and `reassemble()` operate on (§4.4, §12).
- **Section** — a heading plus the content it owns, nested by heading level (§7).
- **Frontmatter** — a leading `---`-delimited YAML block, treated as a non-content
  region (§3).
- **Sizes and `TextUnit`** — the units a document or any unit can be measured in:
  `bytes`, `chars`, `lines`, `words`, `wordtoks`, `sentences`, `paragraphs`, `tokens`.
  The `tokens` unit is an **approximate LLM token estimate** (a characters-per-token
  heuristic), useful for windowing and budgeting; it is never a provider-exact count.
- **Wordtok** — the model’s lowest-level lexical unit, used by the editing view and by
  downstream word-oriented diff/window machinery: a word, a punctuation character, a
  whitespace break, or an embedded HTML tag kept whole, with sentence/paragraph breaks
  represented as sentinel tokens.
  Wordtoks are an implementation-level unit for exact word-level alignment; they are
  **not** LLM tokens (see `tokens` above for that).
- **`SpanRef`** — the durable reference to a piece of the document: a quoted text anchor
  with an offset hint (§11).
- **`DocGraph`** — the serialized JSON projection of a parse (§10).

## 2. Principles and Goals

The foundational principles are the spine; the representation and pragmatic principles
follow from them. Decisions throughout this spec cite the principle they serve.

### Principles

**Tier 1 — Foundational (the spine):**

- **P1. One immutable source, one shared offset space, is the canonical substrate.**
  Every structure aligns to `source_text` by exact `[start, end)` in Unicode code
  points. This, not any one parsed structure, is what unifies the model.
- **P2. Source is canonical; every structural model is a derived, re-derivable
  projection.** Edits go through the source/editing view and re-derive; the parsed model
  is read-mostly and never drifts from the text.
- **P3. Layered parsing; cross-layer relationships are offset-containment queries, not
  stored edges.** The same source is parsed along independent dimensions (textual,
  markdown, document, synthetic), each tagged by `layer`; relations *between* layers are
  interval containment, never persisted edges.
- **P4. Mechanism over menu.** One general query primitive (`collect()`) and two
  composable serialization axes (`include` layers / `detail` payloads); no blessed
  per-kind rollups or fixed detail ladders.
  New capability is one additive layer or detail, not an API refactor.
- **P5. Model ≠ format ≠ implementation.** The contract is a language-neutral JSON
  schema (Pydantic-authored); Python today, Rust/TypeScript later, implement one frozen
  contract.

**Tier 2 — Representation (what the model must faithfully carry):**

- **P6. Exact ground-truth references** (`source_text[s:e] == original_text`).
- **P7. Faithful, complete Markdown structure** — all modern block and inline kinds
  (tables, footnotes, fenced code, blockquotes, inline/block HTML, images); one
  top-level type per block; recursive, fully-populated nesting; bullet vs.
  ordered distinct.
- **P8. Textual structure with clean round-trip** — paragraphs, sentences, and wordtoks
  (see Terminology) as the editing view; edit units and `reassemble()`.
- **P9. Document structure** — heading hierarchy, sections, and TOC, with section
  containment ("which paragraphs are in which section").
- **P10. Synthetic tag structure** — marker-tag regions as a first-class layer (§3).
- **P11. Clean whole-tree round-trip editing** — after arbitrary edits, reproduce a
  document with Markdown-object-level equivalence, and byte-exact equivalence when
  Flowmark-normalized or reconstructed from retained offsets (two distinct equivalence
  levels).

**Tier 3 — Pragmatics (cost, ergonomics, robustness):**

- **P12. Single canonical form, derived views, no stored counts** — sections, slices,
  and tallies are calculated fields; if a view is hard to derive, refine the form.
- **P13. Complete base-block partition** — a flat, ordered, non-overlapping,
  depth-annotated cover of the whole document that reassembles to the source.
- **P14. Serializable projections** — full parse or any slice to language-neutral JSON
  for frontends.
- **P15. Parse cost ≈ one Markdown parse; expensive views are lazy** — pay for costly
  rollups on demand, cached on the immutable source.
- **P16. Approximation where cheap and sufficient** — fast regex sentence segmentation
  and heuristic token sizing are accepted; exactness is reserved for offsets/spans.
- **P17. Lenient input, strict contracts, visible degradation** — parsing never throws
  on malformed input; it degrades to deterministic, documented best-effort structure
  (see Error posture below).
- **P18. Additive evolution** — existing diff/window/wordtok behavior preserved; new
  layers and details are additive.

### Error posture

P17, expanded into the three rules that govern errors throughout the model.
Each layer’s section ends with its specific cases.

1. **Input is handled leniently and deterministically.** Parsing any string yields a
   model; no input — malformed Markdown, broken tables, unclosed fences or tags,
   headingless or structureless documents — raises an exception.
   Every degradation is deterministic and documented in the owning layer’s
   error-handling subsection, and the golden test corpus pins the behavior (including a
   dedicated malformed-input document).
2. **Degradation is visible, never silent.** When the model falls back, the fallback is
   observable in the structure itself: a block that fails to parse as a table *is* a
   `paragraph` node; an unlocatable reference link carries `span=None`; a headingless
   document has `sections() == []`. Consumers can always inspect what was actually
   recognized; nothing is patched over or guessed invisibly.
3. **Internal contracts are validated strictly.** Builder invariants (layer nesting
   guarantees, deterministic node-id assignment) and serialization contracts (JSON-safe
   `attrs`) are checked and **raise** on violation — these indicate bugs in the model,
   never bad input, so failing loudly is correct.
   Where opt-in strictness on *input* exists it is explicit (e.g. the HTML tag finder’s
   `strict=True` raises on unparseable candidates instead of skipping them).
   A uniform opt-in strict-validation / diagnostics pass over a whole parse is specified
   direction, not yet built (§14).

### Goals

Each goal realizes the principle(s) noted.

- **One consolidating structure** (P7, P8, P9). Markdown block, inline, language, and
  document structure in one object, not four tools stitched together.
- **Exact source anchoring** (P1, P6). Every unit references the source by
  `[start, end)`; spans round-trip verbatim; no copies, no drift.
  Offsets are **Unicode code points**.
- **Normalized form, derived views** (P12). One canonical form anchored to the offset
  space; section hierarchy, block-type slices, element rollups, and tallies are
  *calculated fields*, never stored.
  If a view is hard to derive, refine the form.
- **Simplicity with flexibility (mechanism over menu)** (P4). One general query
  primitive (`collect()`), composable serialization layers (`include`), not a fixed menu
  of blessed rollups or detail levels, so the model serves many downstream uses without
  per-need API changes.
- **Markdown-correspondent block types** (P7). One-to-one with Markdown kinds (bullet
  vs. ordered lists distinct); each block has one top-level type; nesting is recursive
  and fully populated.
- **Two block views** (P13). A recursive **structural block tree** (for
  nesting/slicing/queries) and a flat **sequential base-block list** (a complete,
  ordered, non-overlapping partition whose reassembly reproduces the document), so a
  pipeline can process or resequence a document block by block.
- **Density-invariant lists** (P7, P12). Tight and loose lists produce identical
  tallies.
- **Source-canonical references** (P1, P2). A span reference is durable for annotations
  across edits (`SpanRef`): a text quote is the canonical anchor, offsets are
  recomputable hints.
- **Cross-language contract** (P5, P14). `DocGraph` is a plain, parser-agnostic JSON
  schema (Pydantic-authored); Python and any future TypeScript/Rust client are
  implementations of one contract.
- **Dual use** (P8, P11). Analysis of a fixed document *and* an editable model: modify
  units, reassemble, serialize a clean normalized document.
- **LLM/agent-friendly, Python-first, Rust-portable** (P5). Ergonomic from Python and
  from LLM/agent code; a tight spec and thorough tests make a Rust port feasible.
- **Minimal dependencies; additive** (P18). Existing diff/window/wordtok behavior
  preserved.

## 3. The Normalized Form

Everything is aligned by span into a single retained `source_text`. The **canonical
substrate is the source text plus its offset space** (P1): every structure references
the source by exact `[start, end)` (Unicode code points) and is a derived projection.
The **node table** is the primary such projection — a stable set of nodes addressable by
id and span — and is what the serialized contract and cross-layer queries are built on:

1. **Source:** `source_text` plus exact `[start, end)` spans (Unicode code points); each
   unit’s `original_text` is a computed slice, exact by construction.
2. **Node table:** one node per block, inline element, and heading:
   `Node{id, kind, parent, children, source_span, attrs}`. Block containment is
   `parent`/`children`; this is taken from marko’s parse and *referenced*, not
   duplicated.
3. **Language structure:** paragraphs, sentences, and the wordtok view, with spans and
   spacing tokens (the editing view).

A leading YAML frontmatter block (`---`-delimited) is a **non-content region**: it is
excluded from the node table, the block/section views, and the editing view (and so from
every size/prose count), and exposed verbatim via `FlexDoc.frontmatter`. `source_text`
retains it, so spans stay absolute and the document still round-trips.
A leading `---` line with no closing `---` line is **not** frontmatter; it parses as an
ordinary thematic break (a deterministic, lenient reading of the ambiguity).

Why a node table and not a single tree: a document has several hierarchies that overlap
and do not nest: a **section** spans sibling blocks and is not a subtree of the block
tree; **links** are inline ranges; **annotations** target arbitrary spans.
A single canonical tree privileges one hierarchy and forces the rest into bespoke
overlays. A node table gives one id space for blocks *and* inline items, so the
containment tree, section tree, block list, link index, and token stream all share one
id space, and the serialized JSON still presents a `document` root with children as its
top-level shape.

The ergonomic Python views (`blocks()`, `sections()`, `links()`, `base_blocks()`) and
the node table both derive from the same memoized structural parse over the shared
offset space; they are sibling projections, not a store and lookups into it.
This keeps parse cost at roughly one Markdown parse (P15) without coupling every view to
the node-table schema.

**Views over the form.** Several ways to walk the same `source_text`, none of them the
canonical store:

- the blank-line `Paragraph`/`Sentence` **editing view** (the unit set used by
  word-level diffing and windowing);
- the **structural block tree** (the recursive Markdown backbone: slicing, nesting,
  per-item access);
- the **sequential block list** (the flat, non-recursive *base-block* partition, §6);
- the **section tree** (heading hierarchy);
- the **inline/link index**.

The editing view’s block boundaries are unchanged by the structural tree, so there is no
forced migration of the editing unit.

**Parse layers.** Those views are not ad-hoc; each is one **parse layer** over the
shared offset space.
flexdoc parses the same `source_text` along several independent dimensions, each
contributing nodes tagged with their `layer`:

| Layer | Produces | Depends on | Nesting guarantee |
| --- | --- | --- | --- |
| **textual** | paragraphs, sentences, word tokens | — | ordered list |
| **markdown** | block elements (recursive) and inline (links, code, emphasis) | — | tree |
| **document** | section / heading hierarchy and TOC | markdown (headings) | tree |
| **synthetic** | marker-tag regions (see below) | — | tree |

Two consequences define how layers interact:

- **Cross-layer relationships are offset-containment queries, not stored edges.** Within
  a layer, navigate `parent`/`children`; *across* layers, use interval
  containment/overlap ("which markdown blocks are inside this region", “which section
  contains this link”). This is what lets layers overlap and cross-cut without
  contradiction (a section is not a subtree of the block tree; a marked region may open
  mid-block).
- **Each layer declares a nesting guarantee:** well-nested layers project to a tree
  view, ordered-only layers to a sequential list view (the §6 tree-vs-partition
  distinction, generalized).
  The `SpanRef`-targeted annotation layer (§11) is the out-of-band layer, anchored to
  the same offset space.

### The synthetic layer

The **synthetic layer** carries structure that authors or tools introduce *into* the
text with marker tags: a configured subset of XML-style elements whose open/close pairs
delimit regions for chunking, grouping, and in-band metadata.
Each recognized region becomes a node in the synthetic layer with the tag’s name and
attributes in `attrs`, so “which markdown blocks fall inside this region” is the same
offset-containment query as any other cross-layer relationship.

The tag vocabulary is configuration, not code: it is a defined whitelist of tag names,
and adding a tag is adding an entry.
In practice the vocabulary takes a few common shapes:

- **custom extension-style tags**, typically lowercase and hyphenated in the HTML
  custom-element convention (`<my-chunk id="a">...</my-chunk>`), or simple semantic XML
  names such as `<chunk>`;
- **generic HTML containers** — `<div>` and `<span>` are the most common in existing
  documents;
- **comment-delimited directives** such as `<!-- chunk id="foo" -->`, which carry
  structure in Markdown without rendering.

Tags outside the configured vocabulary are inert: they remain ordinary text/HTML in the
other layers and produce no synthetic node.
Because layers are compositional (P3, P18), future extensions can introduce further
parsing-based layers of the same shape — any mechanism that yields spans over the shared
offset space can contribute a layer — without changes to the node table, `collect()`, or
the serialization contract.

Layers are **enabled à la carte**: a configuration, not a fork of the model.

**Status:** the synthetic layer is specified here but not yet implemented in this
package; §14 states what exists today and where the migration is tracked.

**Error handling — synthetic layer (specified behavior).** Unknown tags: inert, by
definition of the whitelist.
An unclosed marker tag forms no region; the tag itself remains visible to the markdown
layer as inline/block HTML (rule 2: the degradation is observable).
Regions that fail to nest (overlapping open/close pairs) violate the layer’s declared
tree guarantee; the implementation must either reject the offending region (lenient:
drop it, keep the text) or relax the layer’s guarantee to ordered-list — this is an open
implementation decision recorded with the migration plan.
Builder-side, whichever policy is chosen is then enforced strictly at node-table build
like every other layer invariant.

## 4. Core Types, Nodes, and Offsets

### 4.1 The source and its offset space

A parse begins from one immutable string, the **source text** (`source_text`). All
positions in the model are **offsets** into this string, counted in **Unicode code
points** (Python’s native string indexing — *not* bytes, and *not* UTF-16 code units).
A **span** is a half-open offset pair `[start, end)`, so `source_text[start:end]` is
exactly the spanned text, empty spans are representable, and adjacent spans share a
boundary without overlapping.

The defining invariant of the whole model (P1, P6):

```
source_text[unit.span[0] : unit.span[1]] == unit.original_text
```

for every source-backed unit — paragraph, sentence, block, node.
A unit’s `original_text` is therefore a *computed slice*, exact by construction; nothing
stores a copy that could drift.

Code points are the canonical unit because they are the one offset basis every language
runtime can reproduce exactly; byte offsets (UTF-8) and UTF-16 units (browsers) are
derivable on demand and may be exposed by `DocGraph` as secondary coordinates, but the
canonical `source_span` is always code points.
(W3C-style position selectors leave the offset basis unresolved across languages; this
model fixes it to code points.)

Documents built from synthetic content rather than a source string (e.g.
`from_wordtoks`, or after `append_sent`) have no original source; for them `source_text`
is the reassembled working text, and the invariant holds against that.

### 4.2 The document object: `FlexDoc`

`FlexDoc` is the package’s entry point and the owner of one parse:

- **Construction:** `FlexDoc.from_text(text)` retains `text` as `source_text`, isolates
  any leading frontmatter, and builds the editing view (paragraphs and sentences)
  eagerly. All other projections are built lazily on first use and cached against the
  immutable source (P15).
- **Owned views:** the `paragraphs` list (the editing view, §4.4); and the derived,
  lazily-cached projections — `blocks()` (§6), `base_blocks()` (§6), `sections()` (§7),
  `links()` (§8), `node_table()` (§4.3), `collect()` (§9), and `graph()` (§10).
- **Offset inversion:** `paragraph_at_offset(o)` and `sentence_at_offset(o)` map an
  absolute offset back to the editing-view unit containing it (or `None` for offsets in
  inter-unit whitespace or outside the document).
  Structural blocks are addressed by their own spans or via `collect(overlaps=...)`.
- **Frontmatter:** `FlexDoc.frontmatter` is the verbatim leading YAML block or `None`
  (§3).
- **Sizing:** `size(unit)` and `size_summary()` measure the document in any `TextUnit`
  (see Terminology), including the approximate LLM `tokens` estimate.

### 4.3 Nodes, kinds, layers, and the node table

A **node** is the uniform record of one parsed element, from any layer:

- `id` — a string id, unique within the parse.
  Ids are assigned by a single **contiguous preorder counter** (`n0001`, `n0002`, ...)
  over a fixed build order (markdown block tree, then document sections, then textual
  paragraphs/sentences, then inline elements), so two parses of the same source produce
  identical ids. This determinism is part of the cross-language contract and is pinned by
  test.
- `kind` — the element’s type: the Markdown block kinds of §5, the inline kinds of §8
  (`link`, `code_span`, `image`, `inline_html`, `footnote_ref`), the document-layer
  `section`, and the textual-layer `sentence`.
- `layer` — which parse dimension produced it (§3).
- `parent` / `children` — **within-layer** containment edges (node ids).
  Cross-layer relationships are never stored; they are offset queries (P3).
- `source_span` — the node’s exact span (§4.1), or `None` for the few elements that have
  identity but no locatable position (e.g. an unresolvable reference link).
- `attrs` — typed metadata as a JSON-safe mapping (`AttrValue`: strings, numbers,
  booleans, `None`, and lists/maps of the same).
  Examples: a heading’s `level`, a list’s `tight`/`ordered`, a link’s `url`/`title`, a
  code block’s `language`. JSON-safety is validated at serialization (§10);
  parser-internal objects never appear in `attrs`.

The **node table** (`NodeTable`) is the flat, id-addressed collection of all nodes in a
parse, plus the list of root ids per layer, over the shared `source_text`. It is a
projection like the others — built *from* the parses, not the store they read from — but
it is the projection queries (§9) and serialization (§10) operate on.

Each layer declares a **nesting guarantee** (§3’s table): tree layers promise that a
child’s span lies within its parent’s; ordered-list layers promise siblings are ordered
and non-overlapping.
These guarantees are **validated strictly when the table is built** — a violation
raises, because it can only mean a bug in a layer builder, never malformed input (Error
posture, rule 3).

### 4.4 The editing view: paragraphs and sentences

The editing view is the mutable face of the model (§12): the units whose text can be
edited and reassembled.

- **`Paragraph`** — one blank-line-delimited unit of the source.
  Carries `original_text` (the verbatim slice), its `sentences`, `offsets`, a `span`, a
  cached Markdown classification `block_type` (§5) with heading helpers
  (`heading_level()`, `heading_title()`), typed `code_info`/`table_info`/`list_info`
  conveniences, and `links()`.
- **`Sentence`** — one sentence within a paragraph.
  `text` is the **normalized, editable** content (what reassembly uses); `original_text`
  is the **verbatim** source slice; `span` is exact when `original_text` is present.
  Sentence boundaries come from flowmark’s span-aware splitter, which never bisects a
  link, code span, autolink, or URL, so sentence spans are exact for all content.
- **`Offsets(doc_offset, block_offset)`** — every paragraph and sentence carries both
  its absolute offset in the document and its offset relative to its enclosing unit (the
  document for a paragraph, the paragraph for a sentence).
- **`SentIndex(para_index, sent_index)`** — the stable address of a sentence within a
  `FlexDoc`, used by editing and diff/window machinery.

A custom sentence splitter may be supplied; offsets for its sentences are recovered by
search and are best-effort where the splitter normalized whitespace (a documented,
visible degradation — `original_text` is absent for such sentences, and `span` falls
back to the normalized length).

### 4.5 Error handling — textual layer

The textual layer accepts *any* string; there is no invalid input.

- **Empty or whitespace-only input** parses to a document with zero paragraphs; sizes
  are zero; iteration yields nothing (boundary sentinels are still emitted for the
  wordtok stream so downstream alignment has stable endpoints).
- **Line endings:** `\r\n` input is tolerated; blank-line detection and frontmatter
  delimiters treat a trailing `\r` as part of the line break.
- **Sentence segmentation is heuristic** (P16): abbreviations or unusual punctuation can
  mis-split. The degradation is visible, not corrupting — every sentence still carries an
  exact verbatim span, so a “wrong” boundary is a presentation choice, never a wrong
  offset.
- **Custom splitters** degrade as described in §4.4: best-effort offsets, observable via
  the missing `original_text`.
- **No strict mode is needed at this layer:** there is nothing to reject — the layer’s
  output is a total function of the input string.

## 5. Block-Type Model

`BlockType` corresponds one-to-one to Markdown block kinds: `heading`, `paragraph`,
`list` (bullet/unordered), `ordered_list`, `list_item`, `table`, `code`, `blockquote`,
`html`, `footnote`, `thematic_break`.

- **Bullet vs. ordered lists are distinct types.** marko’s `List` carries `ordered`;
  `list` is the bullet list, `ordered_list` is enumerated, `list_item` is shared.
- **One top-level type per block,** from its **outer** element: a blockquote wrapping a
  table classifies as `blockquote` at the top level.
  This is what the top-level views and default rollups key on.
- **Nesting is recursive and fully populated.** Every container (blockquote, list item)
  has its block children in the node table, so a table nested inside a blockquote *is* a
  node and is found by a recursive `collect()`. The inner table keeps its own `table`
  kind; default (shallow) rollups attribute it to its enclosing top-level block,
  recursive rollups count it directly.

**List density must not change tallies.** A dense list and the same list written
sparsely are the same list.
In the structural tree a list **always decomposes into `list_item` children regardless
of density**: a loose list is *one* list block with blank-line-separated items, not N
lists, so `len(list.children)` and any tally are density-invariant.
Density is metadata, not structure: a `tight: bool` on the list (CommonMark semantics);
the flag never enters a tally.

**Typed per-block metadata.** Code, table, and list blocks carry parser-authoritative
typed metadata (`flexdoc.docs.block_info`): `CodeInfo` (`language`, `line_count`),
`TableInfo` (`rows`, `cols`, `cells`, `alignments`), and `ListInfo` (`ordered`, `start`,
`max_depth`, `item_count`). It is computed once where the marko element is in hand and
exposed on the structural `Block` (`Block.code_info`/`.table_info`/`.list_info` — the
density-invariant source of truth) and, as a convenience carrying the editing-view
density caveat, on `Paragraph`. The same facts are flattened into the markdown node’s
`attrs`, so they flow into `collect()`/`DocGraph`. Extraction is parser-authoritative
(marko element attributes, never a regex over source); a table column with no alignment
marker is `"default"`, not `None`, so `alignments` is always explicit strings of length
`cols`.

## 6. Block Views: Structural Tree and Sequential Base-Block List

**Terminology.** To avoid overloading “block”:

- **block element** / **inline element:** the Markdown element *class* (CommonMark/mdast
  sense): block-level (heading, paragraph, blockquote, list, list item, table, code, …)
  vs inline (link, code span, emphasis, …).
- **block node:** a node with a block kind in the recursive **structural block tree**
  (`blocks()`); containers (blockquote, list, list item) contain child block nodes.
- **base block:** a unit of the flat **sequential block list** (`base_blocks()`): a
  complete, ordered, non-overlapping partition of the document into the units a pipeline
  processes or a UI resequences.

These are two views over the same shared parse, for two different jobs (and they must
not be conflated; see §9: the tree supports *queries* that may overlap; the base-block
list is a *partition* with a cover invariant).

### Structural block tree: `FlexDoc.blocks() -> list[Block]`

The recursive view (lazy, cached on the immutable `source_text`):

- `Block(type, span, children, tight)`: `span` is trimmed so `source[start:end]` is the
  exact text; `children` holds nested blocks.
  A `list`/`ordered_list` block’s children are its `list_item`s; **containers fully
  populate their block children** (a blockquote’s or list item’s nested blocks are
  present). `tight` carries CommonMark list density on list blocks (`None` elsewhere).
- Resolves what blank-line splitting cannot: a fenced code block stays whole even with
  internal blank lines; a list decomposes into items with nested sublists; a table
  inside a blockquote is reachable.

Block boundaries and spans come straight from flowmark’s parser: every block element
carries an authoritative `element.span = (start, end)` read from marko’s own source
positions (`flowmark.markdown_ast.block_span`), so flexdoc runs no block-detection regex
of its own and makes no block-boundary decisions.
The structure is cross-checked against marko in tests.

### Sequential block list: `FlexDoc.base_blocks() -> list[BaseBlock]`

A **base block** is a `BaseBlock` wrapping a block node (`Block`) with a `depth`; the
**base-block list** is a *partition* of the document: the ordered sequence of base
blocks, each carrying its `depth`. `FlexDoc.base_blocks()` is a thin method over the
`flexdoc.docs.base_blocks.base_blocks(text, *, item_partition_depth=6)` free function
(the partition lives in its own module, distinct from the recursive tree in
`block_tree.py`). It is the view for block-by-block pipelines and outline UIs that
move/resequence blocks (e.g. Notion-style drag-and-drop, where every item is a draggable
unit). flexdoc does not implement such UIs, but the model supports addressing and
reordering at this granularity.
Document manipulation and processing happen base block by base block.

**Frontier.** Leaf and atomic blocks (heading, paragraph, table, code, thematic break,
HTML, and a whole **blockquote**) are each one base block.
**Lists decompose:** each **list item, at every nesting level, is its own base block**
with increasing `depth` (flat-with-depth).
An item holding a nested list contributes a `list_item` **head** block (the marker and
lead content) at depth *d*, then its nested items at *d+1*; any **continuation** content
(paragraphs after or between sublists) follows as base blocks carrying their **own real
block type** (e.g. `paragraph`) at depth *d* — never relabeled `list_item`, so a
consumer can tell a continuation paragraph apart from an independent list item.

How deep lists decompose is one numeric parameter,
`base_blocks(item_partition_depth=6)`:

- `item_partition_depth = N` (default **6**, deep enough for normal nested lists): split
  list items down to *N* nesting levels; list content nested deeper than *N* stays whole
  inside its depth-*N* base block (avoids pathological fan-out on very deep lists).
- `item_partition_depth = -1`: unlimited; split at every nesting level.
- `item_partition_depth = 0`: lists are not split; each list is a single base block
  (coarse mode, i.e. the top-level blocks).

Blockquotes are always one base block regardless of `item_partition_depth`.

**Invariants** (validated and documented): the base-block list is **ordered** by
position, **non-overlapping** by span, and together the spans **cover every
non-whitespace character exactly once** (the gaps are inter-block and structural
whitespace). Every base block retains its exact `source_span`, so **exact source
reconstruction is by slicing the source at those spans** (or via the structural
`blocks()` tree). Reassembling the rendered base-block *text* is **lossy for list-item
continuation content** — list markers and continuation indentation are whitespace
outside the trimmed spans, so naive text concatenation normalizes them; reconstruct from
offsets when exactness matters.
A pipeline may process, edit, or **resequence** base blocks; `depth` is mutable
metadata, so promoting a depth-2 item to depth-1 on a move just changes its rendered
nesting, not a violation.

### Error handling — markdown layer

The Markdown parse is total: every input yields a block tree, with CommonMark’s own
recovery semantics (via marko) deciding how malformed constructs degrade.
The common cases, all deterministic and pinned by the golden corpus (which includes a
dedicated malformed-input document):

- **Unclosed fenced code block:** the fence runs to end of document; everything after
  the opening fence is one `code` block (CommonMark semantics).
  Visible: the block’s span shows exactly what was swallowed.
- **Malformed table:** rows that do not parse as a table degrade to `paragraph` blocks;
  a valid table region keeps its `table` kind and explicit `alignments`.
- **Broken or unclosed HTML:** block-level HTML that marko cannot classify remains an
  `html` block; a single-line tag that marko reads as an inline-HTML paragraph is
  classified `html` by an explicit markup fallback.
  Tags are never “repaired.”
- **Reference links without definitions / unlocatable constructs:** identity is kept,
  `span=None` marks the unlocatable position, and offset-scoped views exclude them (rule
  2: visible, not guessed).
- **Inconsistent list markers / indentation:** CommonMark’s list-interruption and
  lazy-continuation rules apply; the result may split or merge lists, but spans and
  types always describe what the parser actually decided.
- **Strictness:** there is no strict mode at this layer today — CommonMark itself is
  defined to be total — but classification is fully observable, so a caller can layer
  its own validation (e.g. “this document must contain no `html` blocks”) over
  `collect()`. A uniform diagnostics pass is future work (§14).

## 7. Sections and TOC

The document layer derives a heading hierarchy from the markdown layer’s headings — no
re-parse, no stored state.

### Construction rules

- **What starts a section:** exactly the **top-level structural `heading` blocks** of
  `blocks()`. Gating on structural blocks is what makes the layer robust: a `#`-prefixed
  line *inside a fenced code block* is not a heading (the structural tree keeps the
  fence whole), and headings nested inside blockquotes or list items are not top-level
  blocks, so neither starts a document section.
- **Ownership:** a section owns the content from its heading up to (not including) the
  next heading of **equal or higher** level.
  Content between a heading and a deeper heading belongs to the shallower section
  directly (`content`); the deeper heading starts a nested child section.
- **Nesting:** sections nest strictly by level using stack semantics — an incoming
  heading of level *n* closes every open section of level ≥ *n* and attaches to the
  nearest open section of level < *n*, or becomes a root if none is open.
  Multiple top-level headings yield multiple roots.
- **Preamble:** content before the first heading belongs to **no** section.
  It remains fully present in every other view (paragraphs, blocks, sizes); it is simply
  not section-owned.

### The `Section` type

- `heading` — the heading’s editing-view `Paragraph`; `title` is its text without
  markers (an empty string for a bare `#`).
- `level` — the heading level, 1–6, exactly as authored.
- `content` — the section’s **own** paragraphs (excluding the heading line and excluding
  everything owned by child sections).
- `children` — nested `Section`s, in document order.
- `own_paragraphs()` / `subtree_paragraphs()` — the heading plus `content`; the same
  plus all descendants’ paragraphs, in document order.
- `blocks()` — the **structural** block tree (§6) restricted to the section’s own
  content span; density-invariant like the whole-document tree, so per-section
  block-type tallies are spacing-independent.
- `span` — `[heading start, end of last subtree paragraph)`: the full extent of the
  section including its subsections.
- `size(unit, subtree=True|False)` / `size_summary(...)` — sizes in any `TextUnit`,
  rolled up over the subtree by default or restricted to own content; computed by the
  same machinery as `FlexDoc.size`, so every unit (including the approximate LLM
  `tokens` estimate) aggregates uniformly.
- `links()` — links in the section’s subtree, attributed by span containment; links with
  `span=None` are excluded (they cannot be placed by offset).

### Document-level accessors

- `FlexDoc.sections()` — the list of root sections (computed once and cached; the
  returned list is a fresh copy, the `Section` objects shared and read-only by
  contract).
- `FlexDoc.toc()` — the flat table of contents: `(level, title, span)` per heading, in
  document order, by walking the section tree.
- `FlexDoc.section_size_tree(units=...)` — a rendered, indented size rollup per section,
  for quick structural inspection.

### Error handling — document layer

Documents are under no obligation to be well-structured; the section layer is total and
its degradations are visible:

- **No headings at all:** `sections() == []` and `toc() == []`. The document is still
  fully usable through every other view; “no sections” is a true statement about the
  document, not a failure.
- **Preamble-only or mostly-unstructured documents:** the preamble rule covers them —
  content simply belongs to no section, and per-section rollups cover whatever sections
  do exist.
- **Skipped levels** (e.g. an `###` directly under a `#`): no intermediate sections are
  synthesized; the `###` nests directly under the `#`, and its `level` remains 3 as
  authored. Authors’ level choices are preserved, never “corrected.”
- **Out-of-order levels** (a document starting at `##`, or an `#` appearing after
  `###`): handled by the same stack rule — a shallower heading closes deeper open
  sections and becomes a root or sibling as the rule dictates.
  Nothing raises.
- **Malformed near-headings:** `#Title` without a space, or seven-plus `#` characters,
  are not CommonMark headings — they parse as paragraphs and therefore start no section
  (consistent with the markdown layer’s classification, which is the single source of
  truth). A heading with no text (`#` alone) is a real heading with an empty `title`.
- **Setext ambiguity:** a text line underlined with `===`/`---` is a setext heading
  (level 1/2); a bare `---` with no text above is a thematic break; an opening `---` at
  offset 0 with a closing `---` line is frontmatter (§3). All three readings are
  deterministic and mutually exclusive.
- **Duplicate titles** are legal; sections are identified by position and span, never by
  title.
- **Strictness:** none is imposed — but the layer’s output makes validation trivial to
  express externally (e.g. assert `toc()` levels start at 1 and never skip), and a
  built-in opt-in diagnostics pass is specified future work (§14).

## 8. Inline Elements and Links

Inline elements (links, code spans, images, inline HTML, footnote references, …) are
**first-class nodes** whose `parent` is their containing block, with computed
`section`/`sentence` associations, so block↔inline relationships are node edges, and
“links in section 3” is a scoped `collect(kinds={link})`.

- `Link(text, url, title, span)`: identity from `flowmark.markdown_ast.extract_links`
  (reference links resolved, escapes honored, autolinks/images handled), which carries
  no span by design. flexdoc recovers each exact `[start, end)` by reconciling the
  ordered identities with the name-tagged atomic spans from
  `flowmark.atomic_spans.iter_atomic_spans` (`markdown_link` / `autolink` / `bare_url`);
  reference links keep identity but no exact span.
- `link → sentence` via `sentence_at_offset(link.span[0])`.
- **`footnote_ref`**: a footnote reference `[^label]` is a first-class inline node
  (`NodeKind.footnote_ref`) carrying its `label` in `attrs` and an exact span, collected
  like any inline kind (`collect(kinds={NodeKind.footnote_ref}, recursive=True)`). A
  footnote *definition* (`[^label]:`) is a `footnote` block, not a reference.

**Error handling — inline elements.** Inline parsing inherits the markdown layer’s
total, lenient posture.
The cases specific to this sublayer: an identity that cannot be located in the source
keeps its identity with `span=None` and is excluded from offset-scoped rollups; a URL or
link text that appears multiple times resolves in document order (a forward cursor
prevents one unlocatable identity from desyncing the rest); escaped constructs are
honored as escapes, not links.
Nothing raises.

## 9. Derived Views and Rollups

All derived from the canonical source/offset substrate (the node table is the
id-addressed projection used for queries); nothing stores counts.
These structural/query views describe the parsed `source_text`; after editing, re-parse
with `from_text(doc.reassemble())` before structural analysis.
The surface is **one general query primitive, no blessed per-kind rollups**:

```python
collect(*, subtree_of=None, within=None, overlaps=None,
        kinds=None, where=None, recursive=False, inline=False, layer=None) -> list[Node]
```

Available as `doc.collect(...)` (and as the free `collect(table, ...)` over a node
table). Two distinct relations select candidates.
The **tree** relation `subtree_of=` takes a node id and restricts to that node’s
within-layer parent/child subtree (`recursive` descends it).
The **interval** relations are cross-layer and offset-based, each accepting a node id or
`(start, end)` span: `within=` keeps nodes whose span is contained in the region (e.g.
`within=section_id` for everything inside a section); `overlaps=` keeps nodes whose span
merely intersects the region.
Supplying an interval relation scans the whole document, so `within=section_id` needs no
`recursive=True`. `kinds=` selects by node kind (the typed common case); `where=` is a
`Node -> bool` predicate escape hatch; `inline` includes inline nodes (an explicit
inline `kinds` such as `{NodeKind.link}` implies this); `layer=` restricts to parse
layers. It returns **nodes** (each with `span`, `attrs`, edges).
**Counts, values, and groupings are standard Python** over the result, documented with
worked examples, not separate methods:

```python
doc.collect(kinds={NodeKind.table}, recursive=True)        # the tables (values + spans)
len(doc.collect(kinds={NodeKind.table}, recursive=True))   # how many
Counter(n.kind for n in doc.collect(recursive=True))       # tally by kind
doc.collect(within=section_id, kinds={NodeKind.link})      # links in a section
```

Slice-by-block-type, per-section rollups, and element rollups are all expressions of
this one primitive; relationships are node edges.
There are no `tables()`/`code_blocks()` shortcuts to maintain.

**Query vs. partition; do not conflate.** `collect()` is a *query*: it gathers matching
nodes and the results may **overlap** their containers (a table nested in a blockquote
is returned by `collect(kinds={table}, recursive=True)` alongside the blockquote).
That is correct for counting/gathering.
The base-block list (§6) is a *partition*: a complete, ordered, **non-overlapping**
cover for linear processing.
Use `collect()` to ask “how many / which”; use `base_blocks()` to iterate the document’s
content units.

## 10. DocGraph: The Serialized Projection

`DocGraph` is the JSON contract derived from `FlexDoc`, authored as Pydantic models that
emit a JSON Schema. It is parser-agnostic: no marko/Python class names in stable fields.
Shape (abbreviated):

```
DocGraph = {
  schema: "DocGraph/v0.1",
  source:  { format, offset_unit: "unicode_code_points", sha256, text? },
  nodes:   [ Node, ... ],                       # the canonical node table
  views:   { toc, blocks, links, paragraphs, sentences }, # node-id projections
  annotations: [],  layout: [],  provenance: [] # reserved layers (later phases)
}
```

`FlexDoc.graph(*, include=..., detail=...)` builds/serializes it.
**What is built and serialized is controlled by two composable axes**, not a fixed
ladder:

```python
graph()                                                  # default layers, structural core
graph(include={Layer.markdown, Layer.document})          # blocks + sections
graph(include={Layer.markdown}, detail={Detail.text, Detail.inline})  # + node text + inline
graph(include={Layer.markdown, Layer.document, Layer.textual})  # + paragraphs/sentences
```

- **`include` is a set of `Layer`s:** the parse dimensions of §3: `textual`, `markdown`,
  `document`, `synthetic`, later `annotations`/`layout`. Enabling a layer builds and
  serializes its nodes/views; enabling `document` auto-enables its dependency
  `markdown`.
- **`detail` is a small set of payload sub-options:** `text` (per-node source text),
  `inline` (inline nodes), `tokens`, derived coords, controlling richness *within*
  enabled layers.

The structural core (node table, `layer`, and spans) is always present.
Presets are caller-defined `frozenset`s, documented as examples.
A new parse dimension is one additive `Layer`; a new payload category is one additive
`Detail`, never a refactor.

**Error handling — serialization.** Serialization is on the strict side of the error
posture: `attrs` values are validated as JSON-safe at emission and violations raise
(they indicate a builder bug, not bad input); node ids and their assignment order are
deterministic and contract-tested so cross-language clients can reproduce them.
There is no lenient mode for the wire format — a `DocGraph` either conforms to its
schema or is not produced.

## 11. SpanRef and Annotations

`SpanRef` is the one span-reference type used for addressing a piece of the document
from source, parsed model, and rendered output.
It carries two coordinated span kinds:

```
SpanRef = {
  exact: str, prefix?: str, suffix?: str,   # quoted span — CANONICAL durable anchor
  start?: int, end?: int,                   # offset span (code points) — recomputable HINT
}
```

- **Quote canonical, offset a hint.** Every mature annotation system (W3C `oa:Choice`,
  Hypothesis) treats the text quote as the durable anchor and offsets as accelerators,
  because the quote survives edits and re-anchors while offsets shift.
  Within one parse the offset is exact (the fast path); across edits the quote recovers
  the target.
- **Resolution.** model→source is total (a node fills both span and quote).
  source→model is an exact offset fast path, then an exact quote search disambiguated by
  prefix/suffix; `resolve()` is pure (it does not mutate the ref), and
  `resolve_and_update()` is the explicit variant that writes the recomputed offsets
  back. Fuzzy/edit-distance re-anchoring is deferred (not yet implemented).
- **Persistence** is quote-canonical and source-grounded; offsets are an optional
  position hint (`to_persisted(include_position_hint=...)`, dropped by default) and an
  in-memory `node_id` handle is never persisted.
- **Chrome URL Text Fragment convertible:** the quote maps to
  `#:~:text=[prefix-,]exact[,-suffix]` (a lossy projection: prose, word-boundary,
  case-insensitive), generated on demand, never stored.
- **Deferred:** an XPath/DOM `structural_path` and a CRDT `anchor` slot, added only on a
  concrete need.

Annotations are a **stand-off layer**: parsed structure (sections, blocks, links) and
added structure (summaries, notes, suggestions) are the same kind of thing: typed layers
of `SpanRef`-targeted records over immutable source.
**The annotation layer is a later phase** and is expected to be revisited and refined
once v1 is in use; v1 fixes the `SpanRef` contract (at least as expressive as the
Chrome-style `exact`+`prefix`/`suffix` floor) so the node model, schema, and editor
bridge are designed around it.

**Error handling — references.** Resolution failure is a value, not an exception:
`resolve()` returns `None` when the quote is absent from the source or remains ambiguous
after prefix/suffix disambiguation, and callers branch on it (rule 2: the failure is
visible at the call site).
Stale offset hints are harmless by design — the quote re-anchors and
`resolve_and_update()` refreshes the hint explicitly.
Until fuzzy re-anchoring ships (§14), a quote that was itself edited resolves to `None`
rather than to a guess.

## 12. Editing and Serialization

`Sentence.text` is the editable content: edits change what `reassemble()` produces while
the fixed source references (`original_text`, `offsets`, cached `block_type`) keep
describing the original.
So `FlexDoc` doubles as an editable model: modify units, then `reassemble()` to
serialize a new document (optionally normalized by flowmark).
The diff/sliding-window/wordtok machinery operates on this editing view unchanged.

The structural node table is a pure function of the immutable `source_text` (sentence
edits touch the editing view, not `source_text`), so it and its derived views are lazily
cached; the operative contract is “do not reassign `source_text` after parse.”
Edit by editing the `FlexDoc`/source and re-deriving `DocGraph`; an editor bridge
resolves annotations through `SpanRef`. Render helpers emit `data-node-id` /
`data-source-span` so a rendered selection resolves to a node and thence to source.

## 13. Invariants and Non-Goals

Invariants: offset-anchored (code points), the source + offset space being the canonical
substrate (P1); node ids stable within a parse; derived views over one shared parse (no
duplicated content, no stored counts), the node table among them; references are
quote-canonical; additive (existing behavior preserved).

Non-goals: a parallel runtime `BlockDoc`/`SectionDoc` Python model (DocGraph is a
projection, not a competing editable model).
**Naming note:** an abandoned design branch used “FlexDoc” for that competing runtime
model; the name now refers only to the package’s entry-point class.
Other non-goals: blessed per-kind rollups or fixed detail levels; DOM/XPath/CSS
selectors in `SpanRef` (plain-text-first); CommonMark/GFM rendering (flowmark covers
normalization); stored cross-layer edges (cross-layer relationships are
offset-containment queries, §3); exact provider-keyed token counts (`estimate_tokens` is
a heuristic); a thread-safety layer.

**Later phases, not non-goals.** The **synthetic layer** (§3) and **cross-layer
structural edits** (move/wrap/splice anchored on `SpanRef`, generalizing today’s
tag-region edit helpers) are deferred phases, not excluded.
The annotation, operation, provenance, and layout layers are likewise schema-reserved
and built later. The hooks already in place (the `layer` field, offset-containment
`collect()`, `SpanRef`-anchored edits) keep these a small lift rather than a redesign.
§14 states each phase’s current status and where it is tracked.

### Pitfalls and key decisions

Non-obvious choices, each grounded in a principle:

- **The shared offset space — not the node table — is the canonical substrate** (P1).
  The node table is one projection (the id-addressed, layer-tagged,
  serialization-friendly one); it is built *from* the parses, and
  `blocks()`/`sections()`/`links()` derive from the same memoized parse rather than from
  the table’s id space.
  “Single canonical form” holds at the parse + offset space.
- **Cross-layer overlap is expected** (P3). The same logical paragraph appears as
  distinct nodes in distinct layers (a `markdown` block node and a `textual` paragraph
  node over the same span), so a query that does not restrict `layer` returns both.
  This is honest, not a bug; scope with `collect(layer=…)`.
- **Tight vs. loose lists are structurally identical** (P7, P12). Density is
  `Block.tight` metadata only and never enters a tally.
- **Base blocks decompose lists recursively** to `item_partition_depth` (default 6);
  blockquotes are always atomic (P13).
- **Fast/approximate sentence segmentation is accepted** (P16): the regex splitter
  avoids a heavy NLP dependency; offsets stay exact via the span-aware splitter.
- **Fast/approximate token sizing is accepted** (P16): `estimate_tokens` is a heuristic,
  not provider-keyed.
- **Reference links and other unlocatable identities carry `span=None`** and are
  excluded from offset-scoped rollups (e.g. `Section.links()`), since they cannot be
  attributed by offset.
- **Offsets are Unicode code points** (P1); byte/UTF-16 are derived on demand, never
  canonical.
- **Round-trip is Markdown-object-exact, not byte-exact** (P11), except byte-exact via
  retained offsets or after Flowmark normalization — two distinct equivalence levels.

## 14. Implementation Status

**Implemented (in this package, verified by the unit + golden suites):**

- Exact spans over the shared offset space; the editing view (paragraphs/sentences with
  exact verbatim spans); frontmatter isolation as a non-content region.
- The structural block tree `blocks()` (boundaries and spans from flowmark, no regex
  scanner); the `base_blocks()` sequential partition with its non-overlapping cover
  invariant; `ordered_list` and density-invariant lists; typed per-block metadata
  (`CodeInfo`/`TableInfo`/`ListInfo`, §5).
- Sections/TOC/size rollups built from structural headings (§7), cached like the other
  derived views; inline-link rollups and link-aware sentences; inline kinds including
  `footnote_ref` (§8).
- The recursive node table with deterministic contiguous-preorder ids (contract-tested)
  and strict layer-nesting validation at build (§4.3); JSON-safe `attrs` validated at
  serialization; the single `collect()` query primitive (§9); composable
  `include`/`detail` serialization (§10); the `DocGraph` Pydantic schema
  ("DocGraph/v0.1").
- The `SpanRef` contract with exact + prefix/suffix quote resolution and percent-encoded
  text-fragment export (§11).

**Specified here, not yet implemented (each tracked in the extraction plan under
`docs/project/specs/active/`, in the repo’s issue beads, and summarized in `TODO.md`):**

- **The synthetic layer** (§3). Today’s implementation of marker-tag regions
  (`TextNode`/`parse_divs`, currently `<div>`/`<span>`-focused) lives in the chopdiff
  package as a standalone subsystem, not keyed into the node table.
  Migrating it here and re-expressing regions as synthetic-layer nodes is mapped
  concretely in the extraction plan (Stage 4): a builder pass over a configurable tag
  whitelist, an overlap/nesting policy decision, fixtures for regions that cross block
  boundaries, and the moved test suite.
  Moderate difficulty; no changes to the node table, `collect()`, or the schema are
  expected (the `synthetic` layer value is already reserved).
- **The annotation layer** (§11): stand-off, `SpanRef`-targeted records; schema slot
  reserved.
- **Cross-layer structural edits** (§13): operations anchored on `SpanRef`.
- **Fuzzy/edit-distance `SpanRef` re-anchoring** (§11).
- **A uniform opt-in strict-validation / diagnostics pass** over a parse (Error
  posture): today strictness exists piecemeal (builder invariants, serialization
  validation, per-API `strict=` flags); a whole-document diagnostics surface is
  direction, not yet designed.
- **Operation, provenance, and layout layers**: schema-reserved only.

## 15. Background and Further Reading

This spec stands alone; the following are background, not dependencies.

- Research surveys (authored during the model’s design, in chopdiff; copied here as
  history): the cross-language document-model survey
  [`research-2026-05-29-document-model.md`](project/research/research-2026-05-29-document-model.md),
  the span-references survey
  [`research-2026-05-30-span-references.md`](project/research/research-2026-05-30-span-references.md)
  (background for §11), and the layered-parsing brief
  [`research-2026-05-30-multilayer-parsing.md`](project/research/research-2026-05-30-multilayer-parsing.md)
  (background and prior art for §3).
- Dated planning documents under `docs/project/specs/` (active and archived) track the
  incremental work toward this design and reference this spec.
- flowmark v0.7.1 API relied on for spans and splitting: `flowmark.atomic_spans`
  (`iter_atomic_spans`, `split_sentences_with_spans`, named `AtomicSpan`s) and
  `flowmark.markdown_ast` (`block_span`, `walk_elements`, `extract_links`, `Link`).
- Source: `src/flexdoc/docs/flex_doc.py` (the `FlexDoc` core), with the editing units in
  `paragraphs.py`, link extraction in `links.py`, sections in `sections.py`, and the
  structural layer in `block_tree.py`, `block_types.py`, `block_info.py`.

* * *

*This document follows the tbd
[writing style guidelines](https://github.com/jlevy/tbd).*
