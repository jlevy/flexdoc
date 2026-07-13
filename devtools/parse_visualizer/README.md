# FlexDoc Parse Visualizer

Developer-only experiments for inspecting one FlexDoc through several synchronized
visual models. Every view consumes the same exported `DocGraph` and exact wordtok spans.

## Run

From this directory:

```shell
bun install --frozen-lockfile --ignore-scripts
bun run generate
bun run start
```

Open <http://127.0.0.1:4173>. To inspect another document:

```shell
uv run --frozen python export_parse_data.py path/to/document.md
```

The modes are intentionally different experiments:

- **Tracks:** source-aligned intervals across all parse layers
- **Source lens:** exact source tokens with synchronized containment
- **Hierarchy:** D3 icicle and sunburst views of one honest within-layer tree
- **Layer flow:** source-positioned links between overlapping parse layers
- **Graph:** a Cytoscape topology view with structural and cross-layer edges
- **Pretext wrap:** source-preserving line layout with adjustable width
- **Microscope:** a compact local view of the selected span and its wordtoks

This tool is not part of the `flexdoc` package or public API.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
