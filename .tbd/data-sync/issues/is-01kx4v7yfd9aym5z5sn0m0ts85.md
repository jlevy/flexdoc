---
type: is
id: is-01kx4v7yfd9aym5z5sn0m0ts85
title: Make cached structural views mutation-safe
kind: task
status: open
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - api
  - release-0.3
dependencies:
  - type: blocks
    target: is-01kx4v808gd28tns09r81qhs5q
parent_id: is-01kx1w32h8f8920d8kp9xh8ngc
created_at: 2026-07-10T01:45:59.532Z
updated_at: 2026-07-10T01:47:38.339Z
---
Choose and implement frozen Section and Block graphs or defensive copies so public mutation cannot corrupt cached reads. Prefer immutable tuples and frozen records unless compatibility evidence favors copies. Done when nested mutation attempts or copy isolation are tested, cache behavior is documented, and downstream construction still works.
