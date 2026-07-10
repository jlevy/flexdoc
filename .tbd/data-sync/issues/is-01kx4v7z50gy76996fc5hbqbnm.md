---
type: is
id: is-01kx4v7z50gy76996fc5hbqbnm
title: Tier the flexdoc.docs export surface
kind: task
status: open
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - api
  - release-0.3
dependencies:
  - type: blocks
    target: is-01kx4v808gd28tns09r81qhs5q
parent_id: is-01kx1w32h8f8920d8kp9xh8ngc
created_at: 2026-07-10T01:46:00.223Z
updated_at: 2026-07-10T01:47:38.956Z
---
Keep the promoted document-model surface concise while leaving wordtok and diff internals importable from their owning modules. Inventory downstream Chopdiff imports before changing __all__ so it migrates once. Done when export contract tests, downstream migration notes, docs, and the 0.3.0 changelog agree.
