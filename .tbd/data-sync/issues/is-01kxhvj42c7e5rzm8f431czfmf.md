---
type: is
id: is-01kxhvj42c7e5rzm8f431czfmf
title: Split TextRef research from inspector PR
kind: task
status: closed
priority: 2
version: 4
labels: []
dependencies: []
created_at: 2026-07-15T03:01:40.556Z
updated_at: 2026-07-15T03:05:29.787Z
closed_at: 2026-07-15T03:05:29.786Z
close_reason: PR scopes split, descriptions updated, and CI passed for both.
---
Create a research-only branch and PR from the TextRef commits, rewrite PR #17 to contain only the rendered inspector/UI exploration, update both PR descriptions, and verify CI.

## Notes

Split the mixed branch into two current-main-based branches. PR #17 now points to UI-only commit 84dff8a and contains exactly 13 rendered-inspector/devtool files. New draft PR #19 points to research-only commit 5bbd204 and changes only the TextRef research document. Updated both PR descriptions and cross-linked them. Local validation: UI branch make lint-check passed and 367 tests passed; research branch document codespell/diff checks passed and 366 tests passed. Clean-checkout CI passed on both PRs.
