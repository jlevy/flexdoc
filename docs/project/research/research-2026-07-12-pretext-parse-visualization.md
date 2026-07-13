# Research: Pretext and a FlexDoc Parse Explorer

**Date:** 2026-07-12 (last updated 2026-07-12)

**Author:** Codex

**Status:** Complete

## Overview

FlexDoc already represents one source document through several overlapping parse views:
Markdown blocks and inline constructs, document sections, and textual paragraphs and
sentences. This research asks how to expose those layers as a clean, interactive visual
tool and whether [Pretext](https://github.com/chenglou/pretext) is a suitable foundation.

The recommendation is a **DocGraph-backed parse explorer** with synchronized source,
structure, layer-track, and inspector views. Pretext is useful as an optional layout
engine for line geometry, predictive measurement, and virtualization. It should not
become the parser, document model, or source of semantic boundaries.

## Questions to Answer

1. What does Pretext provide, and which parts apply to FlexDoc?
2. Which FlexDoc APIs already support an interactive parse visualization?
3. What data and coordinate-system gaps block a complete paragraph, sentence, word,
   and Markdown view?
4. What should the first useful visualization contain?
5. Should the initial implementation depend on Pretext?

## Scope

This research covers the current FlexDoc and Pretext source trees, a browser-based
developer inspection tool, source-grounded navigation, and a practical implementation
sequence. It includes a developer-only spike with seven synchronized visual models. It
does not select a long-term hosting model or design document editing and annotation
workflows beyond preserving room for them.

Pretext was reviewed at commit
[`ac49b09`](https://github.com/chenglou/pretext/tree/ac49b09b7d83ede19581fa94a8b892b07d309baf)
on `main`. No code from the untrusted checkout was installed, built, or executed.

## Headline Finding

Pretext is not a text parser or tree visualization library. It is a browser text
measurement and line-layout engine. Its most relevant capabilities are:

- measuring wrapped height without DOM layout reads;
- returning line ranges and segment/grapheme cursors;
- laying out each successive line at a different width;
- laying out flattened rich-inline items while retaining their source item indexes;
- supporting `white-space: pre-wrap` for an exact-source-style display; and
- making large, virtualized document views practical.

FlexDoc already owns the semantic information that Pretext lacks. The clean boundary is:

```text
FlexDoc / DocGraph          Semantic truth
  source spans             Canonical Unicode code-point coordinates
  nodes and layers         Paragraph, sentence, Markdown, section, inline identity
  containment queries      Relationships across overlapping layers

Viewer                     Interaction and projection
  selection state          Selected span/node and synchronized panes
  interval index           Visible and containing nodes
  coordinate bridge        Code points <-> UTF-16 <-> layout cursors

Browser DOM + Pretext      Presentation geometry
  DOM                      Accessible text, selection, bidi rendering, actual paint
  Pretext                  Predicted heights, line ranges, custom flow, virtualization
```

## FlexDoc Is Already Close to Viewer-Ready

The following pieces exist today:

- `FlexDoc.node_table()` builds deterministic, id-addressed nodes from the Markdown,
  document, and textual layers.
- Every locatable node uses the same half-open Unicode code-point `source_span`.
- `collect()` supports kind, layer, subtree, containment, and overlap queries.
- `DocGraph` provides a language-neutral JSON/YAML boundary with layer and detail
  selection.
- `Detail.text` embeds source and per-node slices; `Detail.inline` includes links,
  images, code spans, inline HTML, and footnote references.
- Markdown nodes form a tree; sections form a separate tree; paragraphs and sentences
  form an ordered textual view.
- Inline nodes already carry containing section and sentence IDs where applicable.
- `render_node_attrs()` emits `data-node-id` and `data-source-span` for synchronized
  rendered HTML.
- `doc_report()` and the golden artifacts already provide a deterministic textual
  debugger over the same model.

This means the viewer should consume `DocGraph` rather than invent a second browser-side
Markdown model. Pretext's Markdown chat demo uses `marked` and builds its own block and
inline model because it has no upstream semantic graph. FlexDoc does, so copying that
parser architecture would create drift.

## Gaps to Close

### Span-Addressable word tokens

The user-visible requirement includes words. FlexDoc has a mature `wordtok` stream and
`wordtokenize_with_offsets()`, but the current specification intentionally treats
wordtoks as a stream view rather than nodes. The normalized stream does not provide the
complete exact-span records a visualizer needs.

The spike adds the smallest clean projection:

```python
@dataclass(frozen=True)
class WordtokSpan:
    value: str
    exact: str
    span: tuple[int, int]
```

`wordtokenize_with_spans(text)` derives this directly from regex match boundaries
without changing existing normalized wordtok behavior. The exporter carries the
records beside DocGraph nodes and classifies them for display. Making tokens optional
DocGraph nodes can be decided later, after measuring payload and query costs.

The browser must not retokenize source independently. A client-side tokenizer would no
longer visualize what FlexDoc parsed.

### Browser coordinates

DocGraph's canonical offsets are Unicode code points. JavaScript string offsets and DOM
Ranges use UTF-16 code units. Pretext adds segment/grapheme cursors. These are three
different coordinate systems and astral Unicode makes them observably different.

The viewer needs one explicit conversion table built in a linear pass over source:

```text
Unicode code point span <-> UTF-16 span <-> Pretext segment/grapheme cursor
```

For an MVP, the client can build code-point-to-UTF-16 boundaries once. The durable
contract should implement the reserved `Detail.coords` option and serialize optional
`utf16_span` values. Pretext cursor conversion can remain viewer-local: cumulative
segment lengths plus `Intl.Segmenter` map its exposed cursor back to a UTF-16 position.

Pretext's whitespace analysis must not silently change the coordinate space. Use
`whiteSpace: 'pre-wrap'` for a raw source plane, and verify that the prepared segments
reconstruct the exact normalized FlexDoc source before accepting cursor mappings.

### Fully source-grounded rendered Markdown

The current HTML helpers provide node attributes, but FlexDoc does not yet expose one
complete rendered-Markdown artifact in which every rendered block is mapped back to a
node. The first explorer can make the raw source and structure tree authoritative.
A later rendered pane should use the existing Python Markdown parse and a source-aware
renderer, not a second JavaScript Markdown parser.

Emphasis and strong text are not currently NodeKinds. The viewer can render them, but it
must not imply that FlexDoc exposes those inline constructs as independently addressable
semantic nodes until the model actually does.

## Proposed Interaction Model

The strongest visualization is not a single parse tree. It is a set of aligned interval
tracks over canonical source, because FlexDoc's layers overlap:

```text
Document   [---------------- Introduction ----------------][-- Appendix --]
Markdown   [H1][ paragraph ][ list [item][item] ][H2][ code block ]
Textual    [paragraph [sentence][sentence]][paragraph [sentence]    ]
Wordtoks   [word][punct][space][word] ...
Source     # Title\n\nThe first sentence. The second sentence ...
```

Clicking any interval selects a source span. Every pane then resolves from the same
selection:

```text
+ Layer tracks / map + Source or rendered document + Selection inspector  +
| Document           | highlighted exact text      | node id and kind     |
| Markdown           | click and text selection    | layer and attributes |
| Textual            | hover-linked boundaries     | source/code coords   |
| Wordtoks           | viewport virtualization     | parents/containers   |
|                    |                             | exact source/JSON    |
+--------------------+-----------------------------+-----------------------+
| Structure tree / breadcrumbs / contained nodes / DocGraph payload       |
+-------------------------------------------------------------------------+
```

### Core behaviors

- **Layer visibility:** toggle document, Markdown, textual, inline, and wordtok tracks.
- **Semantic zoom:** sections and blocks at overview scale; sentences and tokens appear
  only when the selected or visible source range is small enough.
- **Synchronized selection:** selecting text, a layer interval, or a tree node updates
  every view.
- **Cross-layer breadcrumbs:** show all nodes containing the selection, grouped by
  layer, rather than forcing one false universal parent chain.
- **Bidirectional inspection:** choose a node to highlight source; choose source to list
  overlapping and containing nodes.
- **Payload inspection:** show attributes, exact source slice, code-point and UTF-16
  spans, stable ID, parent/children, `SpanRef`, and serialized JSON.
- **Search and filtering:** filter by `NodeKind`, layer, attribute, node ID, or source
  text.
- **Shareable focus:** encode the selected node/span and active layers in the URL hash.
- **Scalable rendering:** virtualize by block or paragraph for long documents; never
  mount every word token for the entire document at overview scale.

### Visual language

Use one restrained color family per layer, then vary lightness by nesting depth.
Selection should be a separate high-contrast outline rather than another layer color.
Whitespace remains visible in the source plane. Repeated spans from different layers
should appear as aligned tracks, not overlapping translucent text backgrounds, because
overlays become muddy after two or three layers.

## Where Pretext Helps

### Useful immediately in a spike

- `prepare(..., {whiteSpace: 'pre-wrap'})` and `layout()` can predict source-block
  heights for virtualization.
- `layoutWithLines()` and `walkLineRanges()` can produce line boundaries for mapping a
  source span to one or more visual rows.
- `layoutNextLineRange()` supports variable-width layouts, such as leaving room for
  layer labels or an inline inspector callout.
- `prepareRichInline()` retains `itemIndex` on every output fragment. A flattened set of
  DocGraph-backed inline items can therefore keep node ownership after wrapping.
- `measureLineStats()` can drive minimaps, compact previews, and adaptive zoom without
  materializing line strings.

The `rich-note` demo is the best small reference for typed inline fragments. The
`markdown-chat` demo is evidence that Pretext can support a large virtualized Markdown
surface, but its parsing half should be replaced by DocGraph.

### Boundaries not to cross

- Do not treat Pretext segments as FlexDoc word tokens. They implement browser line
  breaking, whitespace, punctuation, CJK, and glue policies for layout.
- Do not use Pretext as a nested markup tree; its rich-inline helper explicitly is not a
  general CSS inline formatting engine.
- Do not base durable references on `LayoutCursor`; it is a segment/grapheme cursor, not
  a raw source offset.
- Do not manually position mixed-direction glyphs from segment widths. Pretext exposes
  bidi metadata, but documents that its widths are insufficient for exact Arabic or
  mixed-direction x-coordinate reconstruction. Let the browser paint selectable text.
- Do not assume server-side operation. The current runtime requires `Intl.Segmenter` and
  Canvas 2D measurement.
- Do not use `system-ui` for measurement on macOS. Wait for `document.fonts.ready` and
  use a named font synchronized with CSS.

## Spike Results

The developer tool in `devtools/parse_visualizer` exports one FlexDoc parse and presents
seven views that share one selection and inspector:

| View | Best use | Finding |
| --- | --- | --- |
| Source-aligned tracks | Primary overview | Best representation of overlapping parse layers; tokens become a barcode at overview scale. |
| Exact source lens | Boundary debugging | Most faithful word, punctuation, whitespace, and tag inspection. |
| D3 icicle and sunburst | Within-layer hierarchy | Compact and legible, but intentionally cannot represent all layers as one tree. |
| Layer flow | Cross-layer containment | Makes correspondences visible without inventing a universal parent relation. |
| Cytoscape graph | Topology debugging | Useful for unusual parent and overlap edges; noisier than tracks for ordinary reading. |
| Pretext wrap | Layout-coordinate experiments | Correctly exposes line ranges at adjustable widths while the browser still paints text. |
| Selection microscope | Local explanation | Best focused view of containers, source context, and exact tokens around one span. |

The most coherent product direction is tracks plus the source lens and microscope as
the default workflow. D3 hierarchy and the graph remain valuable alternate projections.
Pretext earned a bounded role for wrap geometry and future virtualization, but did not
replace browser text rendering or FlexDoc semantics.

The spike also validates the coordinate bridge on astral Unicode: the exporter records
both canonical Unicode code-point spans and browser UTF-16 spans. Pretext cursor mapping
remains local to the layout experiment.

## Other Visualization Libraries

| Library or pattern | What it contributes | Decision |
| --- | --- | --- |
| [D3 hierarchy](https://d3js.org/d3-hierarchy) | Partition, icicle, and radial hierarchy layouts | Used for honest within-layer trees. |
| [Cytoscape.js](https://js.cytoscape.org/) | Interactive graphs, compound nodes, and selectable edges | Used as a topology debugger. |
| [ELK](https://eclipse.dev/elk/) / [elkjs](https://github.com/kieler/elkjs) | Sophisticated automatic graph layout without prescribing a renderer | Consider if larger graphs outgrow the spike's deterministic layout. |
| [Observable Plot](https://observablehq.com/plot/features/marks) | Concise interval and quantitative marks | Strong for future parse metrics, but not needed for the interactive topology. |
| [CodeMirror decorations](https://codemirror.net/examples/decoration/) | Precise editable-source highlighting | Defer until editing is in scope. |
| [React Flow](https://reactflow.dev/) | Node-editor interaction and custom graph components | Too much application framework for a read-only inspector. |
| [brat](https://brat.nlplab.org/features.html) | Proven span-and-arc annotation interactions | Reuse the interaction pattern if semantic relations or annotations are added. |
| [AST Explorer](https://github.com/sxzz/ast-explorer) | Synchronized source and structure inspection | Confirms the value of source/tree linking and shareable focused state. |

## Options Considered

| Criterion | DOM-first viewer | Pretext-driven renderer | Hybrid viewer |
| --- | --- | --- | --- |
| Semantic fidelity | High with DocGraph | High only with a custom bridge | High with DocGraph |
| Exact browser selection and bidi | Native | Difficult | Native |
| Large-document virtualization | Moderate | Strong | Strong |
| Coordinate complexity | Low | High | Medium |
| New build/dependency surface | None or small | JavaScript toolchain required | Deferred until justified |
| Custom/animated layouts | Moderate | Strong | Strong where useful |
| MVP speed | Fastest | Slowest | Fast first phase |

### Recommended: hybrid, staged from DOM-first

Build the semantic interaction and source-span contract with ordinary DOM text first.
Use browser `Range` geometry for the initial highlighted source view. This proves the
selection model, layer tracks, interval queries, and UI shape without adding a second
ecosystem to a Python-only repository.

Then run a bounded Pretext spike against the same viewer API. Keep it only where it
measurably improves long-document resizing, virtualization, or the layer geometry.
This is cleaner than committing the full viewer to Pretext before performance is a
demonstrated constraint.

### Eliminated directions

- **Use Pretext as the parser:** it has no Markdown, paragraph, sentence, section, or
  FlexDoc wordtok semantics.
- **Copy Pretext's `marked`-based demo model:** this duplicates FlexDoc's parser and
  creates two competing sources of truth.
- **Show only a universal tree:** sections, Markdown blocks, sentences, and synthetic
  spans overlap and cannot honestly share one parent hierarchy.
- **Treat YAML/JSON as the visualization:** the current debug report is useful evidence,
  but it does not reveal overlap or allow source-driven navigation.
- **Start with Monaco or CodeMirror:** editor widgets are strong source decorators but
  do not solve the cross-layer map, rendered view, or DocGraph inspector, and introduce
  a larger dependency before editing is in scope.

## Recommended Delivery Sequence

### Phase 1: Data contract and DOM proof

1. Add an exact `wordtokenize_with_spans()` projection without changing existing
   normalized wordtok APIs.
2. Implement `Detail.coords` or a documented client conversion for UTF-16 spans.
3. Define a full-view export equivalent to:

   ```python
   doc.graph(
       include={Layer.textual, Layer.markdown, Layer.document},
       detail={Detail.text, Detail.inline, Detail.tokens, Detail.coords},
   )
   ```

4. Build a dependency-light static viewer with layer tracks, source highlighting,
   structure tree, and inspector.
5. Add a developer entry point that accepts a `FlexDoc` or Markdown path and produces
   an inspectable artifact alongside the existing `dump_views()` outputs.

### Phase 2: Rendered view and Pretext spike

1. Add source-grounded rendered Markdown using the existing Python parse and
   `data-node-id` / `data-source-span` attributes.
2. Measure viewer behavior on small, medium, and large golden documents.
3. Prototype Pretext-backed height prediction and line-range mapping behind the same
   geometry interface.
4. Retain Pretext only if it produces a concrete improvement in resize cost, mounted
   DOM size, or interaction latency.

### Phase 3: Analysis overlays

- annotations and suggested edits anchored by `SpanRef`;
- token diffs and source-grounded change proposals;
- custom/synthetic layers;
- exported screenshots or portable self-contained reports; and
- optional side-by-side views of two parses or two source revisions.

## Packaging and Compatibility

The first data-model changes can be additive. Existing `wordtok` stream behavior and
the default `DocGraph` payload should remain unchanged; token and coordinate detail is
opt-in. Optional new NodeModel fields require a schema compatibility decision and a
schema-version review, even if old consumers can ignore them.

Adding Pretext directly would introduce a JavaScript package manager, lockfile, build
step, and compiled static assets to a Python-only project. Pretext 0.0.8 is MIT-licensed,
has no declared runtime package dependencies, and is old enough for the repository's
14-day cool-off as of this review. Those facts reduce supply-chain risk but do not erase
the maintenance cost. Any dependency addition still requires the repository's normal
security and lockfile review.

Pretext remains a `0.0.x` API. Pin the exact version during a spike and isolate it behind
a small geometry adapter so the viewer's semantic state and DocGraph contract do not
depend on its cursor types.

## Next Steps

- [x] Keep the spike developer-only while the interaction model is evaluated.
- [x] Add exact wordtok spans and explicit code-point-to-UTF-16 coordinates.
- [x] Build synchronized track, source, hierarchy, flow, graph, layout, and microscope
  experiments on a golden document.
- [ ] Add a source-grounded rendered-Markdown pane.
- [x] Run a bounded Pretext line-range and adjustable-width geometry spike.
- [ ] Benchmark and virtualize a genuinely large document before promoting Pretext from
  experiment to infrastructure.

## Methodology

The review inspected FlexDoc's model, graph schema, debug artifacts, renderer helpers,
golden documents, wordtok APIs, specifications, and recent engineering review. The
Pretext repository was cloned into the ignored `attic/pretext` directory and reviewed
at source level, including its public API, layout and rich-inline implementations,
package metadata, changelog, and the rich-note, Markdown chat, and editorial demos.

The initial source review did not execute the checkout. The later isolated developer
spike installed the published `@chenglou/pretext` 0.0.8 package with scripts disabled,
an exact lockfile, and the repository cool-off policy. The spike validates line-range
behavior, not Pretext's published performance claims.

## References

FlexDoc:

- [`flexdoc-spec.md`](../../flexdoc-spec.md)
- [`research-2026-05-30-multilayer-parsing.md`](research-2026-05-30-multilayer-parsing.md)
- [`doc_graph.py`](../../../src/flexdoc/docs/doc_graph.py)
- [`debug.py`](../../../src/flexdoc/docs/debug.py)
- [`render.py`](../../../src/flexdoc/docs/render.py)
- [`wordtoks.py`](../../../src/flexdoc/docs/wordtoks.py)
- [`senior-engineering-review-flexdoc-2026-07.md`](../review/senior-engineering-review-flexdoc-2026-07.md)

Pretext, pinned to the reviewed commit:

- [README and public API](https://github.com/chenglou/pretext/blob/ac49b09b7d83ede19581fa94a8b892b07d309baf/README.md)
- [Package metadata](https://github.com/chenglou/pretext/blob/ac49b09b7d83ede19581fa94a8b892b07d309baf/package.json)
- [Core layout API](https://github.com/chenglou/pretext/blob/ac49b09b7d83ede19581fa94a8b892b07d309baf/src/layout.ts)
- [Rich-inline helper](https://github.com/chenglou/pretext/blob/ac49b09b7d83ede19581fa94a8b892b07d309baf/src/rich-inline.ts)
- [Rich-note demo](https://github.com/chenglou/pretext/blob/ac49b09b7d83ede19581fa94a8b892b07d309baf/pages/demos/rich-note.model.ts)
- [Markdown-chat model](https://github.com/chenglou/pretext/blob/ac49b09b7d83ede19581fa94a8b892b07d309baf/pages/demos/markdown-chat.model.ts)
- [MIT license](https://github.com/chenglou/pretext/blob/ac49b09b7d83ede19581fa94a8b892b07d309baf/LICENSE)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
