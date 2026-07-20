---
type: is
id: is-01ky0sts4ec0d9pdenrz6qn9nw
title: Reject unexpandable point selectors in AnnotationSet
kind: bug
status: closed
priority: 1
version: 4
labels:
  - release-blocker
  - textref
dependencies: []
parent_id: is-01ky0shwff93nvgk9zfd5jb1y6
created_at: 2026-07-20T22:20:03.597Z
updated_at: 2026-07-20T22:35:44.299Z
closed_at: 2026-07-20T22:35:44.299Z
close_reason: Review and tracked fixes completed, covered by regression tests, validated by the full local gate, committed as 739e503, and pushed on codex/release-readiness-textref.
---
AnnotationSet validation checks exact-less spans but omits TextRef's rule for context-free points. A sidecar with a nonzero bare point validates, then expand() fails. Enforce the same point evidence requirement at the sidecar boundary and add a regression test.

## Notes

Regression reproduced before the fix. AnnotationSet now constructs the corresponding complete TextRef during validation, rejecting context-free nonzero points before expand(). Targeted tests and the 407-test suite pass.
