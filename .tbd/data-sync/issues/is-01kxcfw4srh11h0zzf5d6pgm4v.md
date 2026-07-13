---
type: is
id: is-01kxcfw4srh11h0zzf5d6pgm4v
title: Review text-reference microformat research and anchoring robustness
kind: task
status: closed
priority: 2
version: 3
spec_path: docs/project/research/research-2026-07-10-text-reference-microformat.md
labels:
  - research
dependencies: []
created_at: 2026-07-13T01:01:13.911Z
updated_at: 2026-07-13T01:06:47.717Z
closed_at: 2026-07-13T01:06:47.716Z
close_reason: Completed full design review. Recommend eliminating public SnapshotRef in v0.1; use optional source_hash as a strong validator binding position hints to canonical text, keep true archival versioning separate, make selector a discriminated union, and keep exact/fuzzy resolution policy outside the persisted reference. Identified EPUB CFI, HTTP validators/Memento semantics, and GNU patch relaxation as missing prior art; flagged unsafe automatic snapshot/hash rewriting after approximate re-anchoring and Web Annotation state/ambiguity mapping differences.
---
Review docs/project/research/research-2026-07-10-text-reference-microformat.md, inspect related local research, compare against primary literature/specifications, and recommend a simpler reference model with robust edit-tolerant anchoring and a decision on snapshots.
