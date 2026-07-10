---
type: is
id: is-01kv15xy4wvsgxhveg428qpe0v
title: Derive sections() and toc() from the structural heading-block set
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-06-13-metrics-use-case.md
labels: []
dependencies:
  - type: blocks
    target: is-01kv15xzjc48nfvznpbmfbzh3d
  - type: blocks
    target: is-01kv17dwymds7tcmxcwxbfjddz
created_at: 2026-06-13T19:04:24.476Z
updated_at: 2026-06-13T20:16:54.088Z
closed_at: 2026-06-13T20:16:54.088Z
close_reason: null
---
Bug 2 (#6). _section_list re-derives headings from the blank-line paragraph view, dropping tight or marker-preceded headings; contradicts spec section 7. Rewrite to iterate top-level structural heading blocks; reuse or synthesize Section.heading; assign content by offset. Depends on HeadingInfo bead.
