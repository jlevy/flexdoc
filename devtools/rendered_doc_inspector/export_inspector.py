from __future__ import annotations

import argparse
import html
import json
from collections import deque
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from marko import Markdown
from selectolax.parser import HTMLParser
from selectolax.parser import Node as HtmlNode
from strif import atomic_output_file

from flexdoc.docs import Detail, FlexDoc, Layer
from flexdoc.docs.frontmatter import split_frontmatter
from flexdoc.docs.node import LAYER_NESTING, Node, NodeKind, NodeTable

_DANGEROUS_TAGS = frozenset({"embed", "iframe", "link", "meta", "object", "script", "style"})
_ALLOWED_ATTRIBUTES = frozenset(
    {"align", "alt", "checked", "class", "disabled", "href", "src", "start", "title", "type"}
)
_URL_ATTRIBUTES = frozenset({"href", "src"})
_SAFE_URL_SCHEMES = frozenset({"", "http", "https", "mailto"})


def build_inspector_payload(source: str, *, filename: str) -> dict[str, Any]:
    """
    Export a source-grounded rendered document and the nodes needed for hover inspection.

    Raw HTML is sanitized before the browser receives it. The exporter annotates
    elements rendered from addressable Markdown nodes, while cross-layer containment
    remains derived from canonical source spans in the browser.
    """
    layers = (Layer.document, Layer.markdown, Layer.textual)
    doc = FlexDoc.from_text(source)
    graph = doc.graph(
        include=set(layers),
        detail={Detail.inline, Detail.text},
    )
    rendered_html = _render_annotated_html(source, doc.node_table())
    graph_data = graph.model_dump(by_alias=True)
    return {
        "schema": graph_data["schema"],
        "layerNesting": {layer.value: LAYER_NESTING[layer].value for layer in layers},
        "source": {
            "filename": filename,
            "offsetUnit": graph_data["source"]["offset_unit"],
            "text": source,
        },
        "nodes": [_browser_node(node) for node in graph_data["nodes"]],
        "rendered_html": rendered_html,
    }


def _render_annotated_html(source: str, table: NodeTable) -> str:
    _, content_offset = split_frontmatter(source)
    frontmatter_region = source[:content_offset]
    blanked_frontmatter = "".join(
        character if character == "\n" else " " for character in frontmatter_region
    )
    markdown_source = blanked_frontmatter + source[content_offset:]
    rendered = Markdown(extensions=["gfm"]).convert(markdown_source)
    tree = HTMLParser(rendered)
    _sanitize_html(tree)
    _annotate_markdown_nodes(tree, table)
    body = tree.body
    if body is None:
        raise ValueError("Markdown renderer did not produce an HTML body.")
    body_html = body.html
    if body_html is None:
        raise ValueError("Markdown renderer produced an empty HTML body.")
    return body_html.removeprefix("<body>").removesuffix("</body>")


def _sanitize_html(tree: HTMLParser) -> None:
    for tag in _DANGEROUS_TAGS:
        for node in tree.css(tag):
            node.decompose()

    for node in tree.css("*"):
        for attribute, value in list(node.attributes.items()):
            if attribute not in _ALLOWED_ATTRIBUTES:
                del node.attrs[attribute]
                continue
            if attribute in _URL_ATTRIBUTES and (value is None or not _is_safe_url(value)):
                del node.attrs[attribute]


def _is_safe_url(value: str) -> bool:
    scheme = urlsplit(html.unescape(value).strip()).scheme.lower()
    return scheme in _SAFE_URL_SCHEMES


def _annotate_markdown_nodes(tree: HTMLParser, table: NodeTable) -> None:
    queues = _element_queues(tree)
    for node in table.by_layer(Layer.markdown):
        element = _element_for_node(node, table, queues)
        if element is None or node.source_span is None:
            continue
        element.attrs["data-node-id"] = node.id
        element.attrs["data-node-kind"] = node.kind.value
        element.attrs["data-node-layer"] = node.layer.value
        element.attrs["data-source-span"] = f"{node.source_span[0]}:{node.source_span[1]}"


def _element_queues(tree: HTMLParser) -> dict[str, deque[HtmlNode]]:
    selectors = {
        "blockquote": "blockquote",
        "code": "pre",
        "code_span": "code",
        "heading_1": "h1",
        "heading_2": "h2",
        "heading_3": "h3",
        "heading_4": "h4",
        "heading_5": "h5",
        "heading_6": "h6",
        "image": "img",
        "link": "a",
        "list": "ul",
        "list_item": "li",
        "ordered_list": "ol",
        "paragraph": "p",
        "table": "table",
        "thematic_break": "hr",
    }
    queues = {name: deque(tree.css(selector)) for name, selector in selectors.items()}
    queues["code_span"] = deque(
        element
        for element in queues["code_span"]
        if element.parent is None or element.parent.tag != "pre"
    )
    return queues


def _element_for_node(
    node: Node,
    table: NodeTable,
    queues: dict[str, deque[HtmlNode]],
) -> HtmlNode | None:
    queue_name = _queue_name(node, table)
    if queue_name is None:
        return None
    queue = queues[queue_name]
    return queue.popleft() if queue else None


def _queue_name(node: Node, table: NodeTable) -> str | None:
    if node.kind == NodeKind.heading:
        level = node.attrs.get("level")
        return f"heading_{level}" if isinstance(level, int) else None
    if node.kind == NodeKind.paragraph and _is_tight_list_paragraph(node, table):
        return None
    queue_names = {
        NodeKind.blockquote: "blockquote",
        NodeKind.code: "code",
        NodeKind.code_span: "code_span",
        NodeKind.image: "image",
        NodeKind.link: "link",
        NodeKind.list: "list",
        NodeKind.list_item: "list_item",
        NodeKind.ordered_list: "ordered_list",
        NodeKind.paragraph: "paragraph",
        NodeKind.table: "table",
        NodeKind.thematic_break: "thematic_break",
    }
    return queue_names.get(node.kind)


def _is_tight_list_paragraph(node: Node, table: NodeTable) -> bool:
    if node.parent is None:
        return False
    parent = table.node(node.parent)
    if parent.kind != NodeKind.list_item or parent.parent is None:
        return False
    containing_list = table.node(parent.parent)
    return containing_list.kind in {NodeKind.list, NodeKind.ordered_list} and bool(
        containing_list.attrs.get("tight")
    )


def _browser_node(node: dict[str, Any]) -> dict[str, Any]:
    span = node.get("source_span")
    return {
        "id": node["id"],
        "kind": node["kind"],
        "layer": node["layer"],
        "parent": node.get("parent"),
        "children": node.get("children", []),
        "sourceSpan": None if span is None else {"start": span["start"], "end": span["end"]},
        "attrs": node.get("attrs", {}),
        "text": node.get("text"),
    }


def export_inspector(source_path: Path, output_path: Path) -> None:
    """Write the inspector payload atomically for `source_path`."""
    source = source_path.read_text(encoding="utf-8")
    payload = build_inspector_payload(source, filename=source_path.name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with atomic_output_file(output_path) as temporary_path:
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export data for the rendered FlexDoc inspector.")
    parser.add_argument("source", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "generated" / "inspector-data.json",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> None:
    """Export one Markdown source for the developer inspector."""
    args = _parser().parse_args(argv)
    export_inspector(args.source, args.output)


if __name__ == "__main__":
    main()
