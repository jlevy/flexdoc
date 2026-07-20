---
type: is
id: is-01ky0sj7gqrz4jpwy9m0nbyzjw
title: Apply clear release-readiness fixes
kind: task
status: closed
priority: 1
version: 4
labels:
  - release
dependencies: []
parent_id: is-01ky0shwff93nvgk9zfd5jb1y6
created_at: 2026-07-20T22:15:23.414Z
updated_at: 2026-07-20T22:35:44.294Z
closed_at: 2026-07-20T22:35:44.294Z
close_reason: Review and tracked fixes completed, covered by regression tests, validated by the full local gate, committed as 739e503, and pushed on codex/release-readiness-textref.
---
Track and implement only unambiguous, low-risk corrections discovered during the review, with regression coverage and compatibility preservation.

## Notes

Applied three focused release fixes with regression coverage: AnnotationSet now validates every bare selector through the complete TextRef contract, default DocGraph builds reject out-of-bounds annotation hints, and TextRefResolution.resolved requires a resolved document. Also corrected the merged logical-word plan status.
