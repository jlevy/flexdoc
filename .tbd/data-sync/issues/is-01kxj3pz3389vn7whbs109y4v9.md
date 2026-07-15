---
type: is
id: is-01kxj3pz3389vn7whbs109y4v9
title: Add structured source context for TextRefs
kind: feature
status: open
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-07-14-native-textref-integration.md
labels:
  - textref
  - release-0.4
dependencies:
  - type: blocks
    target: is-01kxj3n1xsdhwtqt10ncym5brg
parent_id: is-01kxj2kx1q8dnmyevecnmtka1r
created_at: 2026-07-15T05:24:07.904Z
updated_at: 2026-07-15T05:24:22.262Z
---
Add TextRefContext.context() with the typed resolution result, resolved span, selected source, bounded surrounding lines, and one-based line and Unicode code-point-column labels. Keep line coordinates derived and policies configurable through named limits. Done when whole-document, span, point, section, Unicode, boundary, missing, ambiguous, and source-mismatch contexts are tested.
