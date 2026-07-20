---
type: is
id: is-01ky0shwff93nvgk9zfd5jb1y6
title: Assess release readiness after v0.3.0
kind: epic
status: in_progress
priority: 1
version: 13
labels:
  - release
  - review
dependencies: []
child_order_hints:
  - is-01ky0sj690deaxsvm3nmg1j9yd
  - is-01ky0sj6p37stdvs546bgaenkt
  - is-01ky0sj74ec35t02jkea51qmzp
  - is-01ky0sj7gqrz4jpwy9m0nbyzjw
  - is-01ky0sts4ec0d9pdenrz6qn9nw
  - is-01ky0stsjzvx0fqwvy7ne7gjt6
  - is-01ky0tcg5vffttftqw4x3kvq2f
  - is-01ky0tcgrrbypq340966t9h1fa
  - is-01ky0tch6geesvn6pncy0ksxn0
created_at: 2026-07-20T22:15:12.109Z
updated_at: 2026-07-20T22:38:18.652Z
---
Perform a senior engineering review of all changes on main since v0.3.0, with focused validation of native TextRef support, downstream library compatibility, release automation, packaging, documentation, and test coverage. Apply only clear, safe fixes; verify lint, types, tests, builds, and CI before issuing a release verdict.

## Notes

Review and fix PR #21 is complete and fully green: 7/7 required CI jobs pass across Python 3.11-3.14, macOS, audit, and wheel smoke. The candidate implementation is technically releasable as v0.4.0 once PR #21 is merged. It is intentionally not additive relative to v0.3.0. Do not tag until flexdoc-0e6q resolves how unbounded first-party consumers adopt or cap the semantic break.
