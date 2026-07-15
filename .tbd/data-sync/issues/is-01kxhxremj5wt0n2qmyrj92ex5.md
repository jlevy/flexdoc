---
type: is
id: is-01kxhxremj5wt0n2qmyrj92ex5
title: Align rendered inspector with kpress design system
kind: task
status: closed
priority: 2
version: 4
labels: []
dependencies: []
created_at: 2026-07-15T03:40:05.137Z
updated_at: 2026-07-15T03:54:11.598Z
closed_at: 2026-07-15T03:54:11.597Z
close_reason: KPress-aligned stable inspector layout is committed, pushed, visually verified, and green in CI.
---

## Notes

Reviewed kpress design documentation and CSS sources, mirrored its neutral OKLCH tokens, typography roles, 48rem measure, content card, controls, tables, and responsive treatment in the inspector. Moved hover structure to a fixed-height bottom dock and gave the Markdown toggle a stable width. Browser measurements confirm hover does not change header/workspace document positions; default, split view, and 600px layouts verified. bun run check, make lint-check, 367 tests, and PR #17 CI all pass. Commit f9b1653.
