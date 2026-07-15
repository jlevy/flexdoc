---
type: is
id: is-01kx4v936azv1s1t8hbxq50gdt
title: Define annotation ownership and DocGraph schema v0.2
kind: feature
status: open
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-14-native-textref-integration.md
labels:
  - annotations
  - release-0.4
dependencies:
  - type: blocks
    target: is-01kx4v93vmm64a0ej1ar4fyth2
  - type: blocks
    target: is-01kx4v949qvnf289vy07ncj8a3
parent_id: is-01kx4re3wmzeh04vavf8fz5fst
created_at: 2026-07-10T01:46:37.129Z
updated_at: 2026-07-15T05:09:10.735Z
---
Choose where annotations are owned and how they enter graph serialization, then define ids, kinds, bodies, JSON-safe attributes, provenance, and validation. Introduce an explicit DocGraph schema version without changing v0.1 meaning. Done when v0.1 and v0.2 reader behavior, round trips, invalid records, and ownership flow are tested and documented.
