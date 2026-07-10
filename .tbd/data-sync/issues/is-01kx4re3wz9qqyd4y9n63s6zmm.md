---
type: is
id: is-01kx4re3wz9qqyd4y9n63s6zmm
title: Resolve context-free SpanRef offset-hint ambiguity
kind: bug
status: open
priority: 1
version: 4
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
updated_at: 2026-07-10T01:47:37.731Z
---
A SpanRef with duplicated exact text, start/end hints, and no prefix/suffix can silently anchor to the wrong duplicate after an edit. Decide between returning None for uncorroborated duplicates and adding source identity that proves the hint is current; align code, tests, and spec.
