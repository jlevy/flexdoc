---
type: is
id: is-01ky0tch6geesvn6pncy0ksxn0
title: Coordinate unbounded first-party consumers for v0.4
kind: task
status: open
priority: 1
version: 4
labels:
  - release-blocker
  - compatibility
dependencies: []
parent_id: is-01ky0shwff93nvgk9zfd5jb1y6
created_at: 2026-07-20T22:29:45.295Z
updated_at: 2026-07-20T23:51:57.138Z
---
kash, kash-docs, and kash-media declare flexdoc>=0.3.0 with no <0.4 upper bound, so a v0.4 release will be selected despite documented breaking changes to DocGraph/source identity and word metrics. Their current test suites pass against the candidate, but maintainers must explicitly accept v0.4 semantics or add an upper bound before release.

## Notes

2026-07-20: v0.4.0 is tagged and published; the release notes flag the pin decision for consumers. Unbounded kash/kash-docs/kash-media requirements (flexdoc>=0.3.0) now resolve to 0.4.0 on fresh installs, so accepting v0.4 semantics or adding <0.4 is now an active migration task, not a pre-tag gate.
