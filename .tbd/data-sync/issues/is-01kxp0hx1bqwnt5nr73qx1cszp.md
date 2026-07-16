---
type: is
id: is-01kxp0hx1bqwnt5nr73qx1cszp
title: Collapse DocGraphV2 into one DocGraph contract
kind: task
status: closed
priority: 1
version: 3
spec_path: docs/flexdoc-spec.md
labels: []
dependencies: []
parent_id: is-01kxp0hjtg13jpbafaapmyp7m4
created_at: 2026-07-16T17:45:53.962Z
updated_at: 2026-07-16T18:05:44.750Z
closed_at: 2026-07-16T18:05:44.750Z
close_reason: Unified DocGraph into one source-identifying v0.2 contract, rewrote the TextRef specification from first principles, aligned all APIs and artifacts, and verified local and CI checks.
---
Remove DocGraphV2, SourceInfoV2, build_doc_graph_v2, and the separate schema. Make DocGraph source identity sufficient to bind all graph spans to TextRefs and support optional annotation embedding through one API.
