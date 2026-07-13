---
type: is
id: is-01kxcq4c134dt3ehgx533kdret
title: Review HiNote annotation formats and anchoring design
kind: task
status: closed
priority: 2
version: 4
spec_path: docs/project/research/research-2026-07-10-text-reference-microformat.md
labels:
  - research
  - annotations
  - third-party
dependencies: []
created_at: 2026-07-13T03:08:03.490Z
updated_at: 2026-07-13T03:13:37.474Z
closed_at: 2026-07-13T03:13:37.473Z
close_reason: Reviewed HiNote 0.5.7 at pinned commit 49f6753, documented its storage and fuzzy anchoring model, integrated adapter and resolution lessons into the research brief, and validated with make lint and make test.
---
Check out CatMuse/HiNote to the attic using the tbd shortcut, review its source and persisted/transport formats, compare its highlighting and annotation model with TextRef and the other reviewed tools, and update the text-reference research brief.

## Notes

Reviewed CatMuse/HiNote release 0.5.7 at commit 49f6753725e2af9763fd50ff2633b18be9bcc5b0. Findings: versioned per-file JSON persists inner highlight text, UTF-16 marker-start position, normalized two-sided context, normalized textFingerprint, optional block hint, color, nested comment IDs/timestamps, and virtual file comments. Resolver cascades ID, block+text, exact text+near position, weighted context with absolute and runner-up thresholds, then unique stored text; it greedily assigns stored IDs and automatically rewrites evidence after context matches. Orphan cleanup deletes unmatched records. Added source/representation analysis, adapter map, batch ambiguity guidance, fixtures, methodology, and references.
