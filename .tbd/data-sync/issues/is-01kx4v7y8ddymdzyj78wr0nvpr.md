---
type: is
id: is-01kx4v7y8ddymdzyj78wr0nvpr
title: Define recursive inline collection semantics
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
created_at: 2026-07-10T01:45:59.308Z
updated_at: 2026-07-10T02:20:52.766Z
closed_at: 2026-07-10T02:20:52.765Z
close_reason: "Implemented tri-state inline collection semantics in 9c3e411: recursive omission includes inline descendants, explicit overrides remain authoritative, docs and migration notes aligned, make lint passed, all 345 tests passed, and PR #10 CI passed."
---
Decide whether recursive collection includes inline nodes by default and implement a tri-state or explicit mode if callers must distinguish omission from inline=False. Done when behavior is unambiguous across collect entry points, the tally example is correct, targeted tests cover implicit and explicit modes, and migration notes document the break.
