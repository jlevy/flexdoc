---
type: is
id: is-01kv15xxv3e3dh2ejqwg5mygy0
title: "Fix node_table inline crash: scope inline extraction per block"
kind: bug
status: closed
priority: 1
version: 6
spec_path: docs/project/specs/active/plan-2026-06-13-metrics-use-case.md
labels: []
dependencies:
  - type: blocks
    target: is-01kv15xyznvv68v476cc2d5zb9
  - type: blocks
    target: is-01kv15xzjc48nfvznpbmfbzh3d
  - type: blocks
    target: is-01kv17dwymds7tcmxcwxbfjddz
created_at: 2026-06-13T19:04:24.154Z
updated_at: 2026-06-13T20:16:53.722Z
closed_at: 2026-06-13T20:16:53.721Z
close_reason: null
---
Bug 1 (#6). collect/node_table/graph raise ValueError 'layer nesting violated' on valid Markdown because _build_inline_nodes discovers atomic spans globally and parents by span start. Scope inline discovery to each leaf content block span; parent links by full containment. Keep _validate_layer_nesting intact.
