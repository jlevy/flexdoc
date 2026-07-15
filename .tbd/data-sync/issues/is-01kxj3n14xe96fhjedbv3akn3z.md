---
type: is
id: is-01kxj3n14xe96fhjedbv3akn3z
title: Define TextRef core models and canonical codecs
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
    target: is-01kx4v93df11zeqwtv429bbjfk
  - type: blocks
    target: is-01kx4v936azv1s1t8hbxq50gdt
parent_id: is-01kxj2kx1q8dnmyevecnmtka1r
created_at: 2026-07-15T05:23:04.476Z
updated_at: 2026-07-15T05:37:47.785Z
closed_at: 2026-07-15T05:37:47.783Z
close_reason: Implemented strict TextRef models, canonical source hashing, JSON Schema, URI codec, root exports, and conformance tests; full lint and 371-test suite pass.
---
Implement immutable DocRef, algorithm-qualified source hashes, span/point/section selector models, TextRef, strict extension validation, normative JSON/schema serialization, and the reversible textref:0.1 URI codec. Keep the core pure with no I/O or new dependencies and root-export the public values. Done when whole-document and selector references, invalid inputs, Unicode offsets, source hashes, and JSON/URI round trips have conformance tests.
