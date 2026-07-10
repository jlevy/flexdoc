---
type: is
id: is-01kv15xz9ab82tg8x2zpcm4g2n
title: Add block_at_offset() and fix collect() inline-without-recursive
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
created_at: 2026-06-13T19:04:25.641Z
updated_at: 2026-06-13T20:16:55.331Z
closed_at: 2026-06-13T20:16:55.331Z
close_reason: null
---
#5 items 3 + ergonomics. FlexDoc.block_at_offset(offset)->Block|None completing the inversion set. collect(): inline-kind requests widen the candidate set to all nodes so inline kinds work without recursive=True.
