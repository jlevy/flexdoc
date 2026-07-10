---
type: is
id: is-01kx1w32h8f8920d8kp9xh8ngc
title: Complete the pre-1.0 API cleanup batch
kind: epic
status: in_progress
priority: 2
version: 13
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - api
  - release-0.3
dependencies: []
parent_id: is-01kx4rdq9kt2dy2hzfc2c7fjdw
child_order_hints:
  - is-01kx4v7y0kvqfmh3xmxddy23be
  - is-01kx4v7y8ddymdzyj78wr0nvpr
  - is-01kx4v7yfd9aym5z5sn0m0ts85
  - is-01kx4v7ypn70kb3z756d7nep22
  - is-01kx4v7yxsww8z5reg0fdywafx
  - is-01kx4v7z50gy76996fc5hbqbnm
  - is-01kx4v7zc1rxwx7wh6tj0tav80
  - is-01kx4v7zkbkgas873zg96e5ht5
created_at: 2026-07-08T22:03:05.128Z
updated_at: 2026-07-10T02:34:50.928Z
---
Resolve and implement the remaining breaking-but-cheap API decisions as one 0.3.0 batch: paragraph heading properties, recursive inline collection semantics, structural-view immutability, the navigable-link constant, SpanRef resolution placement, export tiering, frontmatter delimiter tolerance, and Section.size internals. Each child must include focused tests and migration notes. TextUnit is excluded because its StrEnum conversion already landed on PR #9.
