---
type: is
id: is-01kxew9bfsza98jdd9tpsxx6tc
title: Use words for the logical core metric
kind: task
status: in_progress
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-07-13-logical-word-metrics.md
labels: []
dependencies: []
parent_id: is-01kxet6bt9hjzjwr4qvv2b83n7
created_at: 2026-07-13T23:16:38.520Z
updated_at: 2026-07-13T23:16:43.925Z
---
Revise PR #18 so TextUnit.words and core structured/report fields mean logical words, retain TextUnit.raw_words for literal whitespace splitting, remove TextUnit.logical_words, document exactly when normalized words diverge from ordinary expectations, regenerate goldens, validate, push, and wait for CI.
