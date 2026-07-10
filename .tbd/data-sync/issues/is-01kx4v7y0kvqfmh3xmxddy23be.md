---
type: is
id: is-01kx4v7y0kvqfmh3xmxddy23be
title: Make Paragraph heading metadata properties
kind: task
status: open
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - api
  - release-0.3
dependencies:
  - type: blocks
    target: is-01kx4v808gd28tns09r81qhs5q
parent_id: is-01kx1w32h8f8920d8kp9xh8ngc
created_at: 2026-07-10T01:45:59.058Z
updated_at: 2026-07-10T01:47:37.937Z
---
Convert Paragraph.heading_level and heading_title from methods to properties so Paragraph and Block expose consistent metadata and bound methods cannot be mistaken for values. Done when call sites, public docs, focused tests, root-surface expectations, and the 0.3.0 migration note are updated.
