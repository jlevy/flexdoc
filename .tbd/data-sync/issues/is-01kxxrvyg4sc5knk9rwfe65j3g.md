---
type: is
id: is-01kxxrvyg4sc5knk9rwfe65j3g
title: "PR #20 review R1: Make span exact evidence optional"
kind: bug
status: in_progress
priority: 2
version: 3
labels: []
dependencies: []
parent_id: is-01kxnwyc7hcd0djd3p2dknpj9k
created_at: 2026-07-19T18:05:29.988Z
updated_at: 2026-07-19T18:07:13.321Z
---
Formal review 4731209857, PR #20. Replace mandatory unbounded SpanSelector.exact evidence with an optional exact quote plus explicit start/end positions for exact-less, hash-bound spans. Keep existing simple behavior by default; let TextRefContext callers choose a max_exact_chars policy and override include_exact per span/target. Exact-less stale references must fail conservatively. Update schemas, normative spec, usage, research notes, examples, and regression coverage.
