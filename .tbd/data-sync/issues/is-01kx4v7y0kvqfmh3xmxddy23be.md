---
type: is
id: is-01kx4v7y0kvqfmh3xmxddy23be
title: Make Paragraph heading metadata properties
kind: task
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - api
  - release-0.3
dependencies:
  - type: blocks
    target: is-01kx4v808gd28tns09r81qhs5q
parent_id: is-01kx1w32h8f8920d8kp9xh8ngc
created_at: 2026-07-10T01:45:59.058Z
updated_at: 2026-07-10T02:37:53.192Z
closed_at: 2026-07-10T02:37:53.191Z
close_reason: "Converted Paragraph.heading_level and heading_title to properties in d9016f1, pinned heading/non-heading values through the root workflow, aligned active specs and migration notes, make lint passed, all 347 tests passed, and PR #10 CI passed."
---
Convert Paragraph.heading_level and heading_title from methods to properties so Paragraph and Block expose consistent metadata and bound methods cannot be mistaken for values. Done when call sites, public docs, focused tests, root-surface expectations, and the 0.3.0 migration note are updated.
