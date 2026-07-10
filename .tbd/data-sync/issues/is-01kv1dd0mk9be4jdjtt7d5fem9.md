---
type: is
id: is-01kv1dd0mk9be4jdjtt7d5fem9
title: Fuzzy / edit-distance SpanRef re-anchoring (#5 item 4)
kind: feature
status: open
priority: 4
version: 1
spec_path: docs/project/specs/active/plan-2026-06-13-metrics-use-case.md
labels: []
dependencies: []
created_at: 2026-06-13T21:14:58.579Z
updated_at: 2026-06-13T21:14:58.579Z
---
Deferred #5 item 4, design mapped in the metrics plan spec Appendix A. Extend the SpanRef resolution ladder with opt-in fuzzy rungs (offset-hinted, then full-document) behind a new resolve_fuzzy() returning a scored FuzzyMatch; keep resolve() exact-only. Blocked on a supply-chain decision: diff-match-patch (Bitap, needs 14-day cool-off + recorded exception) vs. a stdlib difflib.SequenceMatcher fallback. Spec sections 11/14 are the source of record.
