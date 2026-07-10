---
type: is
id: is-01kx4v93vmm64a0ej1ar4fyth2
title: Define SuggestedEdit and atomic batch application
kind: feature
status: open
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - suggestions
  - release-0.4
dependencies:
  - type: blocks
    target: is-01kx4v949qvnf289vy07ncj8a3
parent_id: is-01kx4re3wmzeh04vavf8fz5fst
created_at: 2026-07-10T01:46:37.811Z
updated_at: 2026-07-10T01:47:42.429Z
---
Define SuggestedEdit, source revision expectations, stale-anchor outcomes, overlap conflicts, deterministic ordering, and atomic failure. Resolve every anchor against one source snapshot and apply accepted edits from highest to lowest offset. Done when batch results are per-edit, no failed batch partially mutates source, and overlap and ambiguity tests cover the contract.
