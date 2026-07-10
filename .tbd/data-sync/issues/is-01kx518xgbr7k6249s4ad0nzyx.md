---
type: is
id: is-01kx518xgbr7k6249s4ad0nzyx
title: Reject zero-length partial context matches
kind: bug
status: closed
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - pr-review
  - span-ref
dependencies: []
parent_id: is-01kx514ekd431tqhbt621nkq69
created_at: 2026-07-10T03:31:22.762Z
updated_at: 2026-07-10T03:32:46.907Z
closed_at: 2026-07-10T03:32:46.906Z
close_reason: Zero-length actual context at document boundaries no longer receives partial-match credit; regression and full suite pass.
---
src/flexdoc/docs/span_ref.py:236-250: precommit review found that _best_match awards partial-match credit when actual_prefix or actual_suffix is empty at a document boundary, because every string starts/ends with the empty string. Zero matched characters cannot disambiguate duplicate quotes. Add a failing boundary regression and require non-empty actual context for partial credit.
