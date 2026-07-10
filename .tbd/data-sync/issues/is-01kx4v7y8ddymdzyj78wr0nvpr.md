---
type: is
id: is-01kx4v7y8ddymdzyj78wr0nvpr
title: Define recursive inline collection semantics
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
created_at: 2026-07-10T01:45:59.308Z
updated_at: 2026-07-10T01:47:38.139Z
---
Decide whether recursive collection includes inline nodes by default and implement a tri-state or explicit mode if callers must distinguish omission from inline=False. Done when behavior is unambiguous across collect entry points, the tally example is correct, targeted tests cover implicit and explicit modes, and migration notes document the break.
