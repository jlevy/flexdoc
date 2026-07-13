from devtools.parse_visualizer.export_parse_data import build_visualization_data


def test_visualization_export_preserves_layers_tokens_and_browser_offsets():
    source = "# Title\n\nAlpha 🤦."
    payload = build_visualization_data(source, "sample.md")

    assert {node["layer"] for node in payload["nodes"]} == {
        "document",
        "markdown",
        "textual",
    }
    assert "link" not in {node["kind"] for node in payload["nodes"]}
    assert "".join(token["exact"] for token in payload["wordtoks"]) == source

    emoji = next(token for token in payload["wordtoks"] if token["exact"] == "🤦")
    assert emoji["source_span"]["end"] - emoji["source_span"]["start"] == 1
    assert emoji["utf16_span"]["end"] - emoji["utf16_span"]["start"] == 2
    assert payload["source"]["text"] == source
