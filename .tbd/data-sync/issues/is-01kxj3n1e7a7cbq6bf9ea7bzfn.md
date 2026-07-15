---
type: is
id: is-01kxj3n1e7a7cbq6bf9ea7bzfn
title: Add FlexDoc TextRefContext and target adapters
kind: feature
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-14-native-textref-integration.md
labels:
  - textref
  - release-0.4
dependencies:
  - type: blocks
    target: is-01kxj3pz3389vn7whbs109y4v9
  - type: blocks
    target: is-01kx4v93vmm64a0ej1ar4fyth2
parent_id: is-01kxj2kx1q8dnmyevecnmtka1r
created_at: 2026-07-15T05:23:04.775Z
updated_at: 2026-07-15T05:52:53.454Z
closed_at: 2026-07-15T05:52:53.453Z
close_reason: Added document-bound TextRefContext, complete public target adapters, semantic sections, exact bound resolution, and visible ownership/location failures with full validation.
---
Add FlexDoc.references(document=...) and a document-bound TextRefContext that computes the source hash once. Map paragraphs, sentences, blocks, base blocks, located links, ordinary nodes, sections, explicit spans, points, and the whole document; reject unlocatable and cross-document targets visibly. Done when every public locatable value round-trips to the intended source span and section targets remain semantic.
