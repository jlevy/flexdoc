---
type: is
id: is-01kxcgehay4ynhegkt6gkc85f8
title: Simplify and revise TextRef microformat research
kind: task
status: closed
priority: 2
version: 3
spec_path: docs/project/research/research-2026-07-10-text-reference-microformat.md
labels:
  - research
  - documentation
dependencies: []
created_at: 2026-07-13T01:11:16.573Z
updated_at: 2026-07-13T01:22:06.212Z
closed_at: 2026-07-13T01:22:06.211Z
close_reason: "Revised the TextRef research brief: removed SnapshotRef, added optional source_hash validator semantics, simplified the typed selector wire shape, separated exact and relaxed resolver policy, made approximate updates conservative, added atomic sidecar hash handling, documented independent edit-robustness evidence, added EPUB CFI/HTTP validator/Memento/GNU patch prior art, and staged extraction after a proven FlexDoc sidecar consumer. Validation passed: local links, make lint, and 353 tests."
---
Revise the TextRef research brief to remove SnapshotRef as a public type, use an optional source hash validator, correct W3C and lifecycle semantics, add EPUB CFI/HTTP validator/Memento/GNU patch prior art, and define an extensible exact-to-fuzzy resolution model.
