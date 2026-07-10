---
type: is
id: is-01kv17dwymds7tcmxcwxbfjddz
title: "Test-suite hardening: adversarial corpus, cross-projection invariants, dogfood real md"
kind: feature
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-06-13-metrics-use-case.md
labels: []
dependencies:
  - type: blocks
    target: is-01kv15xzjc48nfvznpbmfbzh3d
created_at: 2026-06-13T19:30:36.107Z
updated_at: 2026-06-13T20:16:55.635Z
closed_at: 2026-06-13T20:16:55.635Z
close_reason: null
---
Root-cause fix for why the two bugs escaped (see spec Why These Bugs Escaped). Add adversarial corpus docs (inline_pathology, heading_edges, link_taxonomy); add cross-projection invariants to test_model_invariants (toc-count==heading-block count, inline span subset parent on the query surface, public inline collect/graph build, link-form accounting); add a dogfood test parsing every repo .md and asserting invariants only.
