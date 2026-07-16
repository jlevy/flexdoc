---
type: is
id: is-01kxnyvs6pzrb1wb2d29qb5n92
title: "PR #20 review R2: Reject hash-less annotation sidecars"
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01kxnwyc7hcd0djd3p2dknpj9k
created_at: 2026-07-16T17:16:20.566Z
updated_at: 2026-07-16T17:28:20.219Z
closed_at: 2026-07-16T17:28:20.219Z
close_reason: Fixed in 844298e with regression coverage and updated TextRef documentation.
---
PR #20 finding 2. src/flexdoc/text_annotations.py: prevent DocGraph v0.2 from lending trusted source-hash evidence to selectors from an unverified hash-less AnnotationSet; add the stale duplicate-quote regression.
