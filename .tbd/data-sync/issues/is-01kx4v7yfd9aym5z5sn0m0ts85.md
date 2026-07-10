---
type: is
id: is-01kx4v7yfd9aym5z5sn0m0ts85
title: Make cached structural views mutation-safe
kind: task
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - api
  - release-0.3
dependencies:
  - type: blocks
    target: is-01kx4v808gd28tns09r81qhs5q
parent_id: is-01kx1w32h8f8920d8kp9xh8ngc
created_at: 2026-07-10T01:45:59.532Z
updated_at: 2026-07-10T02:28:00.668Z
closed_at: 2026-07-10T02:28:00.667Z
close_reason: "Implemented mutation-safe cached structural views in f004201: Block graphs and TableInfo alignments are immutable tuples, sections return recursively isolated editable views, active specs and migration notes are aligned, make lint passed, all 347 tests passed, and PR #10 CI passed."
---
Choose and implement frozen Section and Block graphs or defensive copies so public mutation cannot corrupt cached reads. Prefer immutable tuples and frozen records unless compatibility evidence favors copies. Done when nested mutation attempts or copy isolation are tested, cache behavior is documented, and downstream construction still works.
