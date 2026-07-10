---
type: is
id: is-01kv15xyznvv68v476cc2d5zb9
title: Add FlexDoc.prose_text() prose-only projection for linting
kind: feature
status: closed
priority: 2
version: 5
spec_path: docs/project/specs/active/plan-2026-06-13-metrics-use-case.md
labels: []
dependencies:
  - type: blocks
    target: is-01kv15xzjc48nfvznpbmfbzh3d
  - type: blocks
    target: is-01kv17dwymds7tcmxcwxbfjddz
created_at: 2026-06-13T19:04:25.332Z
updated_at: 2026-06-13T20:16:54.906Z
closed_at: 2026-06-13T20:16:54.906Z
close_reason: null
---
API gap 4 (#6). Node-table-backed projection over prose blocks (paragraph/heading; exclude code/table/html/frontmatter) using verbatim source slices (preserve spaced em-dash) with inline code dropped and links/images replaced by text. Depends on Bug 1 fix.
