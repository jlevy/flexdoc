---
type: is
id: is-01kx4v936azv1s1t8hbxq50gdt
title: Add the TextRef annotation profile and DocGraph v0.2
kind: feature
status: open
priority: 1
version: 7
spec_path: docs/project/specs/active/plan-2026-07-14-native-textref-integration.md
labels:
  - annotations
  - release-0.4
  - textref
dependencies:
  - type: blocks
    target: is-01kx4v93vmm64a0ej1ar4fyth2
  - type: blocks
    target: is-01kx4v949qvnf289vy07ncj8a3
  - type: blocks
    target: is-01kxj3n1xsdhwtqt10ncym5brg
parent_id: is-01kxj2kx1q8dnmyevecnmtka1r
created_at: 2026-07-10T01:46:37.129Z
updated_at: 2026-07-15T05:24:22.502Z
---
Implement the consumer-owned annotation envelope and one-document sidecar, including bare-selector expansion, stable annotation IDs, motivations, discriminated plain-text bodies, tags, style, captured text, and provenance. Passing annotations explicitly to FlexDoc.graph() selects strict DocGraph/v0.2; omitting them preserves v0.1 exactly. Done when JSON/YAML round trips, invalid records, detached targets, ownership flow, and both graph versions are tested and documented.
