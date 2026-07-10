---
type: is
id: is-01kx4v7yxsww8z5reg0fdywafx
title: Put SpanRef resolution beside the public SpanRef API
kind: task
status: open
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - api
  - anchoring
  - release-0.3
dependencies:
  - type: blocks
    target: is-01kx4v808gd28tns09r81qhs5q
parent_id: is-01kx1w32h8f8920d8kp9xh8ngc
created_at: 2026-07-10T01:45:59.992Z
updated_at: 2026-07-10T01:47:38.747Z
---
After context-free hint semantics are settled, add SpanRef resolution methods or deliberately export the resolver functions from the package root. Prefer methods to avoid generic root names. Done when root API tests, docs, examples, and migration notes establish one obvious resolution path without duplicating logic.
