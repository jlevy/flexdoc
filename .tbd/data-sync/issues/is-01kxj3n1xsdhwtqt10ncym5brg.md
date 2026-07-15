---
type: is
id: is-01kxj3n1xsdhwtqt10ncym5brg
title: Render TextRefs and annotations as deterministic context
kind: feature
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/active/plan-2026-07-14-native-textref-integration.md
labels:
  - textref
  - release-0.4
dependencies:
  - type: blocks
    target: is-01kxj3n2bs84hkv25gv8grx192
parent_id: is-01kxj2kx1q8dnmyevecnmtka1r
created_at: 2026-07-15T05:23:05.272Z
updated_at: 2026-07-15T06:09:54.414Z
closed_at: 2026-07-15T06:09:54.414Z
close_reason: Added deterministic single-reference and merged annotation rendering with canonical URIs, coordinates, point affinity, bounded evidence, explicit elision, adjacent bodies, unresolved groups, golden coverage, and full validation.
---
Add deterministic Markdown-compatible ASCII rendering for a TextRef or annotation batch: merge overlapping windows, place annotation bodies beside resolved source, show stable IDs and target kinds, bound quotes with explicit elision, and group missing, ambiguous, unsupported, and orphaned records. The rendering is derived and never parsed as authoritative data. Done when compact human/LLM fixtures and golden outputs cover each outcome.
