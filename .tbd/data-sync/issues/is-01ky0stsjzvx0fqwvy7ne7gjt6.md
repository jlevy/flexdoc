---
type: is
id: is-01ky0stsjzvx0fqwvy7ne7gjt6
title: Bounds-check annotations in default DocGraph builds
kind: bug
status: closed
priority: 1
version: 4
labels:
  - release-blocker
  - textref
dependencies: []
parent_id: is-01ky0shwff93nvgk9zfd5jb1y6
created_at: 2026-07-20T22:20:04.063Z
updated_at: 2026-07-20T22:35:44.306Z
closed_at: 2026-07-20T22:35:44.306Z
close_reason: Review and tracked fixes completed, covered by regression tests, validated by the full local gate, committed as 739e503, and pushed on codex/release-readiness-textref.
---
build_doc_graph validates embedded selector bounds only indirectly when Detail.text embeds source text. Default graphs can accept out-of-bounds span, point, or section position hints despite having the source snapshot available. Validate bounds before model construction and add regression coverage.

## Notes

Regression reproduced before the fix. build_doc_graph now bounds-checks every embedded annotation against the known source snapshot even when Detail.text is omitted. Span, point, and section-hint coverage added; targeted and full tests pass.
