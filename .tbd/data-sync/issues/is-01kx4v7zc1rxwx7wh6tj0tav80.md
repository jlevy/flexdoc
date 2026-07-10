---
type: is
id: is-01kx4v7zc1rxwx7wh6tj0tav80
title: Decide frontmatter delimiter whitespace tolerance
kind: task
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - api
  - parsing
  - release-0.3
dependencies:
  - type: blocks
    target: is-01kx4v808gd28tns09r81qhs5q
parent_id: is-01kx1w32h8f8920d8kp9xh8ngc
created_at: 2026-07-10T01:46:00.448Z
updated_at: 2026-07-10T02:51:13.345Z
closed_at: 2026-07-10T02:51:13.344Z
close_reason: "Implemented trailing spaces/tabs tolerance for opening and closing frontmatter delimiters in 74fe546 while rejecting leading whitespace, preserving verbatim frontmatter/body offsets, and keeping unclosed thematic-break fallback; docs aligned, make lint passed, all 350 tests passed, and PR #10 CI passed."
---
Decide whether opening and closing frontmatter delimiters tolerate trailing spaces and tabs while continuing to reject leading whitespace. Recommended implementation strips trailing horizontal whitespace only. Done when detection, offset preservation, thematic-break behavior, docs, tests, and migration notes agree.
