---
type: is
id: is-01kxj3n2bs84hkv25gv8grx192
title: Validate native TextRef workflows and compatibility
kind: task
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/active/plan-2026-07-14-native-textref-integration.md
labels:
  - textref
  - release-0.4
dependencies:
  - type: blocks
    target: is-01kx4v949qvnf289vy07ncj8a3
parent_id: is-01kxj2kx1q8dnmyevecnmtka1r
created_at: 2026-07-15T05:23:05.720Z
updated_at: 2026-07-15T06:16:37.079Z
closed_at: 2026-07-15T06:16:37.078Z
close_reason: "Completed all native TextRef design, implementation, workflow, compatibility, schema, golden, documentation, and runnable example work; local validation and PR #20 CI are green."
---
Add runnable extraction provenance, context retrieval, annotation, citation, and edit-target examples plus cross-format schema and golden coverage. Verify public exports, no-selector document references, one-or-many source_refs, DocGraph/v0.1 stability, explicit v0.2 behavior, SpanRef compatibility, and no new dependencies. Done when examples run in CI and make lint and make test pass.
