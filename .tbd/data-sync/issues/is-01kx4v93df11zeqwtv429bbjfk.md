---
type: is
id: is-01kx4v93df11zeqwtv429bbjfk
title: Add quote construction and batch SpanRef resolution
kind: feature
status: open
priority: 2
version: 4
spec_path: docs/project/specs/active/plan-2026-07-14-native-textref-integration.md
labels:
  - anchoring
  - release-0.4
dependencies:
  - type: blocks
    target: is-01kx4v93vmm64a0ej1ar4fyth2
  - type: blocks
    target: is-01kx4v949qvnf289vy07ncj8a3
parent_id: is-01kx4re3wmzeh04vavf8fz5fst
created_at: 2026-07-10T01:46:37.358Z
updated_at: 2026-07-15T05:09:11.002Z
---
Add SpanRef.from_quote and resolve_batch using the same ambiguity and failure contract as single resolution. Start with a clear loop and measure representative batches before introducing an occurrence index. Done when absent, unique, duplicate, contextual, and mixed batch cases have typed outcomes and focused tests.
