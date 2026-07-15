---
type: is
id: is-01kxhzvbfhjb35vms2v0bsdb1r
title: Prevent hover from scrolling inspector page
kind: bug
status: closed
priority: 1
version: 4
labels: []
dependencies: []
created_at: 2026-07-15T04:16:37.360Z
updated_at: 2026-07-15T04:24:34.239Z
closed_at: 2026-07-15T04:24:34.238Z
close_reason: "Replaced page-wide scrollIntoView with source-scroller-only reveal logic in 797926f; regression test, browser verification, local suite, and PR #17 CI all pass."
---

## Notes

Confirmed root cause: sourceActive.scrollIntoView({block: center}) moved window.scrollY from 0 to 116 while sourceCode.scrollTop stayed 0. Replaced it with pure source-scroller reveal math that preserves visible selections and centers/clamps hidden ones. Browser retest keeps window.scrollY at 0 with Markdown visible; bun run check, make lint-check, and 367 tests pass.
