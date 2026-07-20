---
type: is
id: is-01ky0tcg5vffttftqw4x3kvq2f
title: Make TextRefResolution.resolved honor document status
kind: bug
status: closed
priority: 1
version: 4
labels:
  - release-blocker
  - textref
dependencies: []
parent_id: is-01ky0shwff93nvgk9zfd5jb1y6
created_at: 2026-07-20T22:29:44.250Z
updated_at: 2026-07-20T22:35:44.313Z
closed_at: 2026-07-20T22:35:44.313Z
close_reason: Review and tracked fixes completed, covered by regression tests, validated by the full local gate, committed as 739e503, and pushed on codex/release-readiness-textref.
---
The public TextRefResolution model permits construction of a resolved selector with a non-resolved document status, while the resolved convenience property checks only the selector. Make the property enforce the documented document precondition and add regression coverage.

## Notes

TextRefResolution.resolved now requires both DocumentStatus.resolved and a resolved/whole-document selector. Regression coverage protects manually constructed typed results; targeted and full tests pass.
