---
type: is
id: is-01ky0sj6p37stdvs546bgaenkt
title: Audit TextRef behavior and backward compatibility
kind: task
status: closed
priority: 1
version: 5
labels:
  - release
dependencies: []
parent_id: is-01ky0shwff93nvgk9zfd5jb1y6
created_at: 2026-07-20T22:15:22.562Z
updated_at: 2026-07-20T22:39:59.449Z
closed_at: 2026-07-20T22:35:44.288Z
close_reason: Review and tracked fixes completed, covered by regression tests, validated by the full local gate, committed as 739e503, and pushed on codex/release-readiness-textref.
---
Review native TextRef design and implementation in depth, compare the public API and serialized behavior with v0.3.0, and test representative downstream usage for additive safety.

## Notes

Reviewed TextRef models, URI codec, resolvers, FlexDoc context mapping, annotations, DocGraph integration, schemas, rendering, and compatibility docs. Downstream candidate tests passed: chopdiff 44, practical-prose metrics 49, kash 223, kash-docs 50 with all locked optional extras, and kash-media 1. Protected consumers pin ==0.2/0.3 or <0.4; kash, kash-docs, and kash-media remain unbounded and require explicit v0.4 coordination under flexdoc-0e6q.
