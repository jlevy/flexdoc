"""
Node table: a flat, id-addressed table of all parsed elements in a document,
covering three layers (markdown, document, textual) over the same source text.

`build_node_table(doc)` constructs the table once from a `FlexDoc`; the result
is cached lazily on `FlexDoc.node_table()` (safe because `source_text` is
immutable after parse).

The source string and its offset space are canonical; the node table is the
id-addressed query/serialization projection over that substrate, assigning ids
and layer tags. The block tree, section tree, and inline index are sibling
projections sharing the same source/offset substrate.
"""

# pyright: reportImportCycles=false
# The TYPE_CHECKING import of FlexDoc creates a type-only cycle with flex_doc.py
# (which runtime-imports build_node_table). No runtime cycle exists.

from __future__ import annotations

from typing import TYPE_CHECKING

from flowmark.atomic_spans import iter_atomic_spans

from flexdoc.docs.block_tree import Block
from flexdoc.docs.interval_index import IntervalIndex
from flexdoc.docs.links import LinkForm
from flexdoc.docs.node import (
    LAYER_NESTING,
    AttrValue,
    Layer,
    NestingGuarantee,
    Node,
    NodeKind,
    NodeTable,
)

if TYPE_CHECKING:
    from flexdoc.docs.flex_doc import FlexDoc
    from flexdoc.docs.sections import Section


# Atomic-span pattern names that map to inline NodeKinds.
_INLINE_ATOMIC_KINDS: dict[str, NodeKind] = {
    "markdown_link": NodeKind.link,
    "inline_code_span": NodeKind.code_span,
    "html_open_tag": NodeKind.inline_html,
    "html_close_tag": NodeKind.inline_html,
}


def _next_id(counter: list[int]) -> str:
    """Deterministic id from a preorder counter: `n0001`, `n0002`, ..."""
    idx = counter[0]
    counter[0] += 1
    return f"n{idx:04d}"


def _node_kind_for_block(block: Block) -> NodeKind:
    """Map a `BlockType` value to its corresponding `NodeKind`."""
    return NodeKind(block.type.value)


def _build_markdown_nodes(
    blocks: list[Block],
    parent_id: str | None,
    counter: list[int],
    nodes: dict[str, Node],
) -> list[str]:
    """
    Recursively build markdown-layer nodes from the structural block tree.
    Returns the list of child ids for the caller to wire into its `children`.
    """
    child_ids: list[str] = []
    for block in blocks:
        nid = _next_id(counter)
        child_ids.append(nid)
        attrs: dict[str, AttrValue] = {}

        # Heading level from the block's parser-authoritative HeadingInfo.
        if block.heading_info is not None:
            attrs["level"] = block.heading_info.level

        if block.tight is not None:
            attrs["tight"] = block.tight
            attrs["ordered"] = block.type.value == "ordered_list"

        # Typed, parser-authoritative metadata flows into the markdown node's attrs (and
        # thus DocGraph/collect) as flat keys; the structs themselves stay on the Block.
        if block.code_info is not None:
            attrs["language"] = block.code_info.language
            attrs["line_count"] = block.code_info.line_count
        if block.table_info is not None:
            attrs["rows"] = block.table_info.rows
            attrs["cols"] = block.table_info.cols
            attrs["cells"] = block.table_info.cells
            attrs["alignments"] = list(block.table_info.alignments)
        if block.list_info is not None:
            attrs["start"] = block.list_info.start
            attrs["max_depth"] = block.list_info.max_depth
            attrs["item_count"] = block.list_info.item_count

        node = Node(
            id=nid,
            kind=_node_kind_for_block(block),
            layer=Layer.markdown,
            parent=parent_id,
            children=[],
            source_span=block.span,
            attrs=attrs,
        )
        nodes[nid] = node

        if block.children:
            node.children = _build_markdown_nodes(block.children, nid, counter, nodes)
    return child_ids


def _build_inline_nodes(
    source_text: str,
    doc: FlexDoc,
    all_nodes: dict[str, Node],
    counter: list[int],
) -> None:
    """
    Add inline nodes to the node table: links, images, and reference definitions from
    `doc.links()` (reference resolution and parser-authoritative `LinkForm`s), and code
    spans, inline HTML, and footnote references from flowmark's `iter_atomic_spans`.

    Links/images/definitions are parented to the innermost markdown block that *fully
    contains* the construct (climbing from the start-innermost node), so a span chosen by
    start alone can never escape its parent. The atomic pass scans each leaf content block
    *separately*, so backtick (code-span) and tag pairing is bounded to one block and an
    inline node can never straddle a block boundary (the layer-nesting invariant holds by
    construction; see `_validate_layer_nesting`). Section and sentence associations are
    stored in `attrs`.
    """
    # Index the structural/section/sentence nodes built so far (inline nodes are not yet
    # added) for offset-containment lookups, avoiding a full-table scan per inline element.
    index = IntervalIndex.from_nodes(all_nodes)

    # Frontmatter is a non-content region: skip any inline element located inside it (see
    # FlexDoc.frontmatter). Block/section/textual nodes are already frontmatter-free.
    content_offset = doc._content_offset()
    seen_spans: set[tuple[int, int]] = set()

    def cross_layer_attrs(start: int) -> dict[str, AttrValue]:
        attrs: dict[str, AttrValue] = {}
        section_id = index.innermost(start, Layer.document, kind=NodeKind.section)
        if section_id:
            attrs["section"] = section_id
        sent_nid = index.innermost(start, Layer.textual, kind=NodeKind.sentence)
        if sent_nid:
            attrs["sentence"] = sent_nid
        return attrs

    def innermost_container(span: tuple[int, int]) -> str | None:
        """The innermost markdown node whose span fully contains `span`, found by climbing
        from the start-innermost node until containment holds."""
        nid = index.innermost(span[0], Layer.markdown)
        while nid is not None:
            nspan = all_nodes[nid].source_span
            if nspan is not None and nspan[0] <= span[0] and span[1] <= nspan[1]:
                return nid
            nid = all_nodes[nid].parent
        return None

    def attach(nid: str, parent: str | None) -> None:
        if parent and parent in all_nodes:
            all_nodes[parent].children.append(nid)

    # Leaf content blocks, captured now (before inline nodes are attached as children) so a
    # block that later receives an inline link/image child is still scanned for code spans
    # and tags. Code blocks (verbatim) and thematic breaks (no content) are excluded.
    leaf_nodes = [
        n
        for n in all_nodes.values()
        if n.layer == Layer.markdown
        and not n.children
        and n.kind not in (NodeKind.code, NodeKind.thematic_break)
        and n.source_span is not None
    ]

    # Links, images, and reference definitions via doc.links() (all forms).
    for link in doc.links(forms=set(LinkForm)):
        if link.form == LinkForm.image:
            kind = NodeKind.image
        elif link.form == LinkForm.reference_definition:
            kind = NodeKind.link_ref_def
        else:
            kind = NodeKind.link

        attrs: dict[str, AttrValue] = {"url": link.url, "text": link.text}
        if kind == NodeKind.link:
            attrs["form"] = link.form.value
        if link.title:
            attrs["title"] = link.title

        if link.span is None:
            # Unlocatable reference link: keep identity, no position or parent.
            nid = _next_id(counter)
            all_nodes[nid] = Node(
                id=nid, kind=kind, layer=Layer.markdown, parent=None, source_span=None, attrs=attrs
            )
            continue
        if link.span[0] < content_offset or link.span in seen_spans:
            continue
        seen_spans.add(link.span)
        attrs.update(cross_layer_attrs(link.span[0]))
        nid = _next_id(counter)
        parent = innermost_container(link.span)
        all_nodes[nid] = Node(
            id=nid,
            kind=kind,
            layer=Layer.markdown,
            parent=parent,
            source_span=link.span,
            attrs=attrs,
        )
        attach(nid, parent)

    # Code spans, inline HTML, and footnote refs: scan each leaf content block's slice so
    # pairing is bounded to one block. Links and images are already handled above.
    for leaf in leaf_nodes:
        assert leaf.source_span is not None
        b_start, b_end = leaf.source_span
        for atomic in iter_atomic_spans(source_text[b_start:b_end]):
            if not atomic.is_atomic or atomic.name is None:
                continue
            if atomic.name not in _INLINE_ATOMIC_KINDS:
                continue
            span = (b_start + atomic.start, b_start + atomic.end)
            if span[0] < content_offset or span in seen_spans:
                continue

            if atomic.name == "markdown_link":
                # Links/images come from doc.links(); here only recognize a footnote
                # reference `[^label]` (not a definition marker `[^label]:`).
                link_text = source_text[span[0] : span[1]]
                is_def_marker = span[1] < len(source_text) and source_text[span[1]] == ":"
                if not (
                    link_text.startswith("[^") and link_text.endswith("]") and not is_def_marker
                ):
                    continue
                kind = NodeKind.footnote_ref
            else:
                kind = _INLINE_ATOMIC_KINDS[atomic.name]

            seen_spans.add(span)
            inline_attrs: dict[str, AttrValue] = {}
            if kind == NodeKind.code_span:
                inline_attrs["content"] = atomic.text.strip("`").strip()
            elif kind == NodeKind.inline_html:
                inline_attrs["tag"] = atomic.text
            elif kind == NodeKind.footnote_ref:
                inline_attrs["label"] = source_text[span[0] + 2 : span[1] - 1]
            inline_attrs.update(cross_layer_attrs(span[0]))

            nid = _next_id(counter)
            all_nodes[nid] = Node(
                id=nid,
                kind=kind,
                layer=Layer.markdown,
                parent=leaf.id,
                source_span=span,
                attrs=inline_attrs,
            )
            attach(nid, leaf.id)


def _build_section_nodes(
    sections: list[Section],
    parent_id: str | None,
    counter: list[int],
    nodes: dict[str, Node],
) -> list[str]:
    """Build document-layer section nodes from the heading hierarchy."""
    child_ids: list[str] = []
    for sec in sections:
        nid = _next_id(counter)
        child_ids.append(nid)
        attrs: dict[str, AttrValue] = {
            "level": sec.level,
            "title": sec.title,
        }
        node = Node(
            id=nid,
            kind=NodeKind.section,
            layer=Layer.document,
            parent=parent_id,
            children=[],
            source_span=sec.span,
            attrs=attrs,
        )
        nodes[nid] = node
        if sec.children:
            node.children = _build_section_nodes(sec.children, nid, counter, nodes)
    return child_ids


def build_node_table(doc: FlexDoc) -> NodeTable:
    """
    Construct a `NodeTable` from a `FlexDoc`, building nodes from three layers:

    - **markdown**: every structural block from the recursive block tree, plus
      inline elements (links, code spans, images, inline HTML).
    - **document**: one node per section from the heading hierarchy.
    - **textual**: paragraphs and sentences from the editing view.

    Node ids are deterministic preorder indexes (`n0001`, `n0002`, ...), stable
    within a parse of the same source text.
    """
    source_text = doc.source_text or doc.reassemble()
    nodes: dict[str, Node] = {}
    roots: list[str] = []
    counter: list[int] = [1]

    # Markdown layer: structural blocks. Reuse the doc's cached structural parse so the
    # node table and the `blocks()` view share one parse over the shared offset space.
    blocks = doc.blocks()
    root_ids = _build_markdown_nodes(blocks, None, counter, nodes)
    roots.extend(root_ids)

    # Document layer: sections from heading hierarchy.
    sections = doc.sections()
    section_root_ids = _build_section_nodes(sections, None, counter, nodes)
    roots.extend(section_root_ids)

    # Textual layer: paragraphs and sentences.
    for para in doc.paragraphs:
        para_nid = _next_id(counter)
        para_node = Node(
            id=para_nid,
            kind=NodeKind.paragraph,
            layer=Layer.textual,
            parent=None,
            children=[],
            source_span=para.span,
            attrs={},
        )
        nodes[para_nid] = para_node
        roots.append(para_nid)
        for sent in para.sentences:
            sent_nid = _next_id(counter)
            sent_node = Node(
                id=sent_nid,
                kind=NodeKind.sentence,
                layer=Layer.textual,
                parent=para_nid,
                children=[],
                source_span=sent.span,
                attrs={"text": sent.text},
            )
            nodes[sent_nid] = sent_node
            para_node.children.append(sent_nid)

    # Inline nodes (markdown layer): links, code spans, images, inline HTML.
    _build_inline_nodes(source_text, doc, nodes, counter)

    _validate_layer_nesting(nodes, roots)
    return NodeTable(nodes=nodes, roots=roots, source_text=source_text)


def _validate_layer_nesting(nodes: dict[str, Node], roots: list[str]) -> None:
    """
    Check each layer's declared `NestingGuarantee` (`LAYER_NESTING`) over the built
    table: in a tree layer a child's span lies within its parent's; in an ordered-list
    layer sibling spans (and the layer's roots) are ordered by start and
    non-overlapping. These are builder invariants, not input validation — malformed
    Markdown must still build (P17) — so a violation is a bug in a layer builder and
    raises here rather than silently corrupting queries and serialization downstream.
    """
    for node in nodes.values():
        if node.parent is None:
            continue
        parent = nodes[node.parent]
        if LAYER_NESTING[node.layer] is not NestingGuarantee.tree:
            continue
        if parent.source_span is None or node.source_span is None:
            continue
        p_start, p_end = parent.source_span
        c_start, c_end = node.source_span
        if not (p_start <= c_start and c_end <= p_end):
            raise ValueError(
                f"layer nesting violated: {node.layer} node {node.id} span "
                f"{node.source_span} not within parent {parent.id} span {parent.source_span}"
            )

    ordered_layers = {
        layer for layer, g in LAYER_NESTING.items() if g is NestingGuarantee.ordered_list
    }
    for layer in ordered_layers:
        layer_roots = [nodes[rid] for rid in roots if nodes[rid].layer == layer]
        sibling_groups = [layer_roots] + [
            [nodes[cid] for cid in n.children] for n in nodes.values() if n.layer == layer
        ]
        for group in sibling_groups:
            prev_end: int | None = None
            for sib in group:
                if sib.source_span is None:
                    continue
                if prev_end is not None and sib.source_span[0] < prev_end:
                    raise ValueError(
                        f"ordered layer {layer} has out-of-order or overlapping sibling "
                        f"{sib.id} at span {sib.source_span}"
                    )
                prev_end = sib.source_span[1]
