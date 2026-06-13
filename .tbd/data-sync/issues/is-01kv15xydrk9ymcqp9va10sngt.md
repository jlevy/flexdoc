---
type: is
id: is-01kv15xydrk9ymcqp9va10sngt
title: Add HeadingInfo to Block; node table reads heading level from it
kind: feature
status: closed
priority: 1
version: 6
spec_path: docs/project/specs/active/plan-2026-06-13-metrics-use-case.md
labels: []
dependencies:
  - type: blocks
    target: is-01kv15xy4wvsgxhveg428qpe0v
  - type: blocks
    target: is-01kv15xzjc48nfvznpbmfbzh3d
  - type: blocks
    target: is-01kv17dwymds7tcmxcwxbfjddz
created_at: 2026-06-13T19:04:24.760Z
updated_at: 2026-06-13T20:16:53.389Z
closed_at: 2026-06-13T20:16:53.378Z
close_reason: null
---
API gap 1 (#6). Add HeadingInfo(level,title) + heading_info_for mirroring CodeInfo/TableInfo/ListInfo; carry Block.heading_info + Block.heading_level. node_table._build_markdown_nodes reads it, retiring the hand-rolled hash-counting/setext scan. Single source for the Bug 2 fix level/title.
