---
type: is
id: is-01kx4v7zc1rxwx7wh6tj0tav80
title: Decide frontmatter delimiter whitespace tolerance
kind: task
status: open
priority: 2
version: 2
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
updated_at: 2026-07-10T01:47:39.171Z
---
Decide whether opening and closing frontmatter delimiters tolerate trailing spaces and tabs while continuing to reject leading whitespace. Recommended implementation strips trailing horizontal whitespace only. Done when detection, offset preservation, thematic-break behavior, docs, tests, and migration notes agree.
