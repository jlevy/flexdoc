---
type: is
id: is-01kty73hwxs0pytf8wjb4n1f90
title: Enforce LAYER_NESTING in build_node_table
kind: task
status: closed
priority: 2
version: 3
labels: []
dependencies: []
created_at: 2026-06-12T15:27:13.821Z
updated_at: 2026-06-12T15:36:04.629Z
closed_at: 2026-06-12T15:36:04.629Z
close_reason: LAYER_NESTING validated in build_node_table (tree containment + ordered-sibling checks); whole corpus passes
---
Review F7. Validate per-layer nesting guarantees (tree layers: child span within parent span) at table build so synthetic-layer bugs fail loudly.
