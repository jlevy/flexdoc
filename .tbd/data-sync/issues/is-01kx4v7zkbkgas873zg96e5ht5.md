---
type: is
id: is-01kx4v7zkbkgas873zg96e5ht5
title: Remove the temporary FlexDoc from Section.size
kind: task
status: open
priority: 3
version: 2
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - internals
  - release-0.3
dependencies:
  - type: blocks
    target: is-01kx4v808gd28tns09r81qhs5q
parent_id: is-01kx1w32h8f8920d8kp9xh8ngc
created_at: 2026-07-10T01:46:00.682Z
updated_at: 2026-07-10T01:47:39.381Z
---
Extract shared paragraph-size aggregation so Section.size does not instantiate a temporary FlexDoc or rely on the circular-import workaround. Done when behavior is unchanged, existing size coverage passes, and the workaround is removed without a new wrapper-only API.
