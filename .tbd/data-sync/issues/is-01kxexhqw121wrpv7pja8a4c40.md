---
type: is
id: is-01kxexhqw121wrpv7pja8a4c40
title: Add core TextRef section target type
kind: task
status: closed
priority: 2
version: 4
labels: []
dependencies: []
created_at: 2026-07-13T23:38:41.921Z
updated_at: 2026-07-13T23:57:23.235Z
closed_at: 2026-07-13T23:57:23.234Z
close_reason: "Research design updated, published to PR #17, and CI verified."
---
Update the TextRef research brief so v0.1 explicitly models whole-document, point, span, and semantic section targets; define section boundaries, recovery behavior, JSON/YAML/URI projections, and future extensibility; validate, commit, push, and update PR #17.

## Notes

Defined four v0.1 TextRef target kinds: selector-free whole document, arbitrary source span, zero-width point, and CommonMark heading section with durable start and optional end anchors. Clarified that spans need not align to Markdown parsing; table, row, cell, and header-cell annotations use spans until structural identity is required. Updated JSON, YAML, URI, context rendering, resolution, requirements, decisions, recommendations, fixtures, evidence, and limitations. Validation: make lint-check passed; make test passed (354 tests); document codespell, diff, link, and numbering checks passed. Committed as c449bd1, pushed to PR #17, and CI passed.
