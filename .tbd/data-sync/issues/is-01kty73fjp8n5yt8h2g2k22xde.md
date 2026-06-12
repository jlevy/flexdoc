---
type: is
id: is-01kty73fjp8n5yt8h2g2k22xde
title: Drop deprecated collect() aliases (scope/contains); make collect keyword-only
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies: []
created_at: 2026-06-12T15:27:11.446Z
updated_at: 2026-06-12T15:31:02.894Z
closed_at: 2026-06-12T15:31:02.893Z
close_reason: collect() aliases removed; keyword-only; tests rewritten to subtree_of/within
---
Review F1. Remove scope (positional) and contains params from flexdoc.docs.collect.collect and the TextDoc.collect bridge; fully keyword-only after table. Rewrite alias tests in tests/docs/test_collect.py to subtree_of/within.
