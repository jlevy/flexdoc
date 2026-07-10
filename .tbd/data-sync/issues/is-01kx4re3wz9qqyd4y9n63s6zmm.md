---
type: is
id: is-01kx4re3wz9qqyd4y9n63s6zmm
title: Resolve context-free SpanRef offset-hint ambiguity
kind: bug
status: open
priority: 1
version: 1
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels: []
dependencies: []
parent_id: is-01kx4rdq9kt2dy2hzfc2c7fjdw
created_at: 2026-07-10T00:56:55.966Z
updated_at: 2026-07-10T00:56:55.966Z
---
A SpanRef with duplicated exact text, start/end hints, and no prefix/suffix can silently anchor to the wrong duplicate after an edit. Decide between returning None for uncorroborated duplicates and adding source identity that proves the hint is current; align code, tests, and spec.
