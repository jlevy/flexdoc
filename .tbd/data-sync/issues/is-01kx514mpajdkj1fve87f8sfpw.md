---
type: is
id: is-01kx514mpajdkj1fve87f8sfpw
title: Treat empty SpanRef context as absent
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
created_at: 2026-07-10T03:29:02.665Z
updated_at: 2026-07-10T03:32:46.723Z
closed_at: 2026-07-10T03:32:46.722Z
close_reason: Empty configured SpanRef context is treated as absent in fast-path verification and slow-path scoring; regression and full suite pass.
---
src/flexdoc/docs/span_ref.py:146-155: PR #10 review thread PRRT_kwDOS4aaIc6Pw1cE reports that prefix="" or suffix="" incorrectly corroborates the offset fast path on duplicate quotes. Add a failing regression, make empty context semantically absent across resolution, and preserve non-empty context disambiguation.
