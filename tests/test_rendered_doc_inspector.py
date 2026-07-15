from textwrap import dedent

from devtools.rendered_doc_inspector.export_inspector import build_inspector_payload


def test_inspector_export_maps_nodes_and_sanitizes_rendered_html():
    source = dedent(
        """
        # Heading

        A [safe link](https://example.com) and `code`.

        <img src="javascript:alert(1)" onerror="alert(2)">
        <script>alert(3)</script>
        """
    ).strip()

    payload = build_inspector_payload(source, filename="example.md")

    assert payload["schema"] == "DocGraph/v0.1"
    assert payload["layerNesting"] == {
        "document": "tree",
        "markdown": "tree",
        "textual": "ordered_list",
    }
    assert payload["source"]["text"] == source
    assert {node["layer"] for node in payload["nodes"]} == {
        "document",
        "markdown",
        "textual",
    }
    link = next(node for node in payload["nodes"] if node["kind"] == "link")
    paragraph = next(node for node in payload["nodes"] if node["id"] == link["parent"])
    assert link["id"] in paragraph["children"]
    rendered_html = payload["rendered_html"]
    assert 'data-node-id="' in rendered_html
    assert "<h1" in rendered_html
    assert "<script" not in rendered_html
    assert "onerror" not in rendered_html
    assert "javascript:" not in rendered_html
