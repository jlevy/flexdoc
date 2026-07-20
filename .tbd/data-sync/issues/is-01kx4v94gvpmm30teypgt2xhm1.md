---
type: is
id: is-01kx4v94gvpmm30teypgt2xhm1
title: Validate and publish FlexDoc 0.4.0
kind: task
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - release
  - release-0.4
dependencies:
  - type: blocks
    target: is-01kx4v94yy19tzzeng4kng990j
parent_id: is-01kx4re3wmzeh04vavf8fz5fst
created_at: 2026-07-10T01:46:38.490Z
updated_at: 2026-07-20T23:51:56.750Z
closed_at: 2026-07-20T23:51:56.747Z
close_reason: "0.4.0 published 2026-07-20: tag and GitHub Release at 60a19b0 via release.yml, wheel and sdist on PyPI, fresh-venv install from PyPI verified (version, parse, TextRef URI round-trip)."
---
Phase 2 gate. Run the complete validation matrix, review schema compatibility and public examples, publish 0.4.0 through the tag-driven workflow, and smoke-test the artifact. Done when versioned annotation and workflow APIs install and round-trip as documented.

## Notes

2026-07-20 independent senior review of the v0.4.0 candidate (PR #21 head 739e503): make lint/lint-check clean, 407 tests pass, pip-audit clean, tag-derived 0.4.0 wheel built from an isolated clone and smoke-tested in a fresh venv (version, TextRef flow, packaged schemas), PR CI 7/7 green. Breaking-change catalog and release-notes reference: docs/project/review/senior-engineering-review-v0.4-release-2026-07.md. Remaining before tag: flexdoc-0e6q downstream pins; retitle changelog Unreleased section at release.
