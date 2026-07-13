"""
Export the complete source-grounded model consumed by the developer parse visualizer.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from strif import atomic_output_file

from flexdoc import Detail, FlexDoc, Layer
from flexdoc.docs.wordtoks import (
    WordtokSpan,
    is_entity,
    is_number,
    is_tag,
    is_word,
    wordtokenize_with_spans,
)

DEFAULT_OUTPUT = Path(__file__).parent / "generated" / "parse-data.json"


def _utf16_boundaries(text: str) -> list[int]:
    boundaries = [0]
    for char in text:
        boundaries.append(boundaries[-1] + len(char.encode("utf-16-le")) // 2)
    return boundaries


def _wordtok_kind(item: WordtokSpan) -> str:
    if item.exact.isspace():
        return "whitespace"
    if is_tag(item.value):
        return "tag"
    if is_entity(item.value):
        return "entity"
    if is_number(item.value):
        return "number"
    if is_word(item.value):
        return "word"
    return "punctuation"


def build_visualization_data(source_text: str, title: str) -> dict[str, Any]:
    """
    Build one JSON-safe payload containing every parsed layer, inline nodes, exact
    wordtok spans, and browser-native UTF-16 coordinates.
    """
    doc = FlexDoc.from_text(source_text)
    graph = doc.graph(
        include={Layer.textual, Layer.markdown, Layer.document},
        detail={Detail.text, Detail.inline},
    )
    payload = graph.model_dump(by_alias=True)
    utf16 = _utf16_boundaries(source_text)

    for node in payload["nodes"]:
        span = node.get("source_span")
        if span is not None:
            node["utf16_span"] = {
                "start": utf16[span["start"]],
                "end": utf16[span["end"]],
            }

    wordtoks = []
    for index, item in enumerate(wordtokenize_with_spans(source_text)):
        start, end = item.span
        wordtoks.append(
            {
                "id": f"w{index + 1:05d}",
                "value": item.value,
                "exact": item.exact,
                "kind": _wordtok_kind(item),
                "source_span": {"start": start, "end": end},
                "utf16_span": {"start": utf16[start], "end": utf16[end]},
            }
        )

    table = doc.node_table()
    payload.update(
        {
            "title": title,
            "roots": [
                node_id for node_id in table.roots if node_id in {n["id"] for n in payload["nodes"]}
            ],
            "wordtoks": wordtoks,
            "line_starts": [
                0,
                *[index + 1 for index, char in enumerate(source_text) if char == "\n"],
            ],
        }
    )
    return payload


def export_visualization_data(source_path: Path, output_path: Path) -> None:
    """Parse `source_path` and atomically write its visualization payload."""
    source_text = source_path.read_text(encoding="utf-8")
    payload = build_visualization_data(source_text, source_path.name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with atomic_output_file(output_path) as temp_path:
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export a Markdown document for the FlexDoc parse visualizer."
    )
    parser.add_argument("source", type=Path, help="Markdown source file")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    export_visualization_data(args.source, args.output)
    print(f"Exported {args.source} to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
