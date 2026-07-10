---
type: is
id: is-01kx4re3wz9qqyd4y9n63s6zmm
title: Resolve context-free SpanRef offset-hint ambiguity
kind: bug
status: closed
priority: 1
version: 6
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - anchoring
  - release-0.3
dependencies:
  - type: blocks
    target: is-01kx4v7yxsww8z5reg0fdywafx
  - type: blocks
    target: is-01kx4v808gd28tns09r81qhs5q
parent_id: is-01kx4rdq9kt2dy2hzfc2c7fjdw
created_at: 2026-07-10T00:56:55.966Z
updated_at: 2026-07-10T02:16:28.448Z
closed_at: 2026-07-10T02:16:28.447Z
close_reason: "Implemented the 0.3.0 decision in cb0c388: context-free position hints cannot select duplicated quotes, unique quotes still resolve through search, and code/spec/changelog plus a red-green regression are aligned. Local lint, 344 tests, and PR #10 CI pass."
---
A SpanRef with duplicated exact text, start/end hints, and no prefix/suffix can silently anchor to the wrong duplicate after an edit. Decide between returning None for uncorroborated duplicates and adding source identity that proves the hint is current; align code, tests, and spec.
