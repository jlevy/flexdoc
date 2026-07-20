---
type: is
id: is-01ky0tch6geesvn6pncy0ksxn0
title: Coordinate unbounded first-party consumers for v0.4
kind: task
status: open
priority: 1
version: 2
labels:
  - release-blocker
  - compatibility
dependencies: []
parent_id: is-01ky0shwff93nvgk9zfd5jb1y6
created_at: 2026-07-20T22:29:45.295Z
updated_at: 2026-07-20T22:34:46.984Z
---
kash, kash-docs, and kash-media declare flexdoc>=0.3.0 with no <0.4 upper bound, so a v0.4 release will be selected despite documented breaking changes to DocGraph/source identity and word metrics. Their current test suites pass against the candidate, but maintainers must explicitly accept v0.4 semantics or add an upper bound before release.

## Notes

Compatibility suites pass against the candidate, but kash, kash-docs, and kash-media specify flexdoc>=0.3.0 without <0.4 and will therefore accept documented 0.4 breaking semantics. Before tagging, explicitly accept the new word-count/DocGraph behavior in those packages or cap them below 0.4.
