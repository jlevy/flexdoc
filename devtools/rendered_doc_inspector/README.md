# Rendered FlexDoc Inspector Spike

This developer-only spike tests one interaction model: present a clean rendered
document first, then reveal its FlexDoc structure only when the reader points at or
focuses content. Optional Markdown and DocGraph panes follow the active source span.

## Scope

The minimum implementation answers these questions:

- Can one hover resolve a rendered element into document, Markdown, textual, sentence,
  and inline nodes without showing permanent parse chrome?
- Can the same span highlight and auto-scroll exact Markdown source without disturbing
  native text selection and copy/paste?
- Can block and inline mappings be exported from FlexDoc without adding another browser
  Markdown parser?
- Can the same payload render FlexDoc's document and Markdown trees plus its textual
  ordering without treating the renderer's parse tree as document data?
- Does the interaction remain understandable with nested lists, blockquotes, tables,
  links, and code spans?

The spike includes a source-to-HTML exporter, one rendered document surface, a compact
hover path, mutually exclusive synchronized Markdown and DocGraph panes, copy actions
for the rendered and source views, and a KPress-aligned system/light/dark theme chooser.

It does not implement editing, annotations, URL-addressable selections, virtualization,
arbitrary synthetic layers, or a public FlexDoc API. Compatibility is not applicable:
the directory is an isolated developer experiment and has no external consumers.

## Run

```shell
cd devtools/rendered_doc_inspector
uv run --frozen python export_inspector.py example.md
bun run start
```

Then open <http://127.0.0.1:4173>.

## Spike Decision

Keep this as a reference implementation, not a public API. Browser validation supports
the rendered-first interaction model:

- The default surface reads as a normal document and exposes no parse boxes before
  interaction.
- Hovering or focusing a block or inline construct produces a useful cross-layer path,
  including nested sections, lists, textual paragraphs, sentences, and inline nodes.
- Active and ancestor outlines use outward visual offsets instead of padding, so nested
  wrappers remain distinct without changing text layout.
- The optional Markdown pane follows the exact source span and scrolls only its own
  source viewport when necessary, without moving the page or changing native selection
  behavior.
- The optional DocGraph pane renders the document and Markdown trees plus the ordered
  textual paragraph/sentence hierarchy. It follows the active node without moving the
  page.
- The settings gear applies and persists system, light, or dark theme preferences.
- Unicode code-point spans are converted explicitly before slicing browser strings.
- Copy actions use the Clipboard API and fall back to selecting the complete surface
  when clipboard permission is unavailable.

FlexDoc's source string and Unicode code-point offsets are canonical. The tree pane
renders the `DocGraph/v0.1` serialization projection. The document and Markdown layers
declare tree nesting; the textual layer declares ordered-list nesting and uses
paragraph/sentence parent-child links. Source-span containment relates nodes across
layers. The pane does not expose Marko's rendering parse as FlexDoc structure.

The main technical risk is rendered-node mapping. The spike renders with Marko and then
correlates safe HTML elements with FlexDoc Markdown nodes in source order. This works for
the fixture's headings, paragraphs, nested lists, blockquote, table, code, link, and code
span, but two independent parser traversals can drift on unsupported extensions or raw
HTML. A maintained implementation should attach `data-node-id` and `data-source-span`
during FlexDoc's parser-authoritative render pass.

Sentence containment works well in the hover path even though sentences are not literal
DOM wrappers. Exact word hover remains unresolved because rendered text and Markdown
source are different coordinate surfaces. Emphasis is also visible but not addressable
because FlexDoc does not currently model it as an inline node.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
