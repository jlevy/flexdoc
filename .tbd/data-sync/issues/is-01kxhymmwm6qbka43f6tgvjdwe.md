---
type: is
id: is-01kxhymmwm6qbka43f6tgvjdwe
title: Refine inspector hover borders
kind: task
status: closed
priority: 2
version: 4
labels: []
dependencies: []
created_at: 2026-07-15T03:55:29.043Z
updated_at: 2026-07-15T04:00:11.694Z
closed_at: 2026-07-15T04:00:11.693Z
close_reason: "Implemented and verified full-perimeter inspector border hierarchy; committed in 2658ff5 and CI passed on PR #17."
---

## Notes

Replaced asymmetric left accents with 1px full-perimeter ancestor outlines, 2px direct-target outlines, and uniform trail borders. Verified nested active/container states in the live browser. bun run check, make lint-check, and 367 tests pass.
