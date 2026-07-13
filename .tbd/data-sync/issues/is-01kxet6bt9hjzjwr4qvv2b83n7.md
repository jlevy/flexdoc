---
type: is
id: is-01kxet6bt9hjzjwr4qvv2b83n7
title: "Spec: Add robust logical word metrics"
kind: epic
status: open
priority: 1
version: 11
spec_path: docs/project/specs/active/plan-2026-07-13-logical-word-metrics.md
labels:
  - github-issue-16
dependencies: []
child_order_hints:
  - is-01kxetekcysw1m0h557170c2zz
  - is-01kxetekmghzkrhe1wzgn1d50d
  - is-01kxetekwayf1t4yag0zvm01hn
  - is-01kxetem3rw8fjhgzy2j2g51sp
  - is-01kxetembq1w0mh10jmqx0nyn3
  - is-01kxetemkczpzfqsfsaeq7b76w
  - is-01kxew9bfsza98jdd9tpsxx6tc
created_at: 2026-07-13T22:40:03.400Z
updated_at: 2026-07-13T23:16:38.520Z
closed_at: null
close_reason: null
---
Review and implement GitHub issue #16 end to end. Define explicit raw and logical word metrics, decide the public TextUnit compatibility policy, update token/read-time consumers, validate across prose, CJK, code, and machine text, and publish a PR with a validation plan.

## Notes

Reopened: User refined the public naming after PR publication: core word fields should use words with logical semantics and explicit divergence documentation.
