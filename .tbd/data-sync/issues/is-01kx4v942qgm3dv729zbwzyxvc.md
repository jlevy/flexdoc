---
type: is
id: is-01kx4v942qgm3dv729zbwzyxvc
title: Add opt-in normalized SpanRef re-anchoring
kind: feature
status: open
priority: 2
version: 3
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - anchoring
  - release-0.4
dependencies:
  - type: blocks
    target: is-01kx4v949qvnf289vy07ncj8a3
  - type: blocks
    target: is-01kv1dd0mk9be4jdjtt7d5fem9
parent_id: is-01kx4re3wmzeh04vavf8fz5fst
created_at: 2026-07-10T01:46:38.038Z
updated_at: 2026-07-10T01:47:43.041Z
---
Add an opt-in whitespace-collapsed and case-normalized matching tier that reports strategy and score without changing exact resolve semantics. Build a small edited-document corpus first. Done when unique, ambiguous, Unicode, whitespace, and case changes are evaluated and the corpus justifies the shipped threshold and failure behavior.
