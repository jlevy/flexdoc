---
type: is
id: is-01kty73g8akn6fakgwvbhnj660
title: Settle the export surface (docs + html __init__, DEFAULT_INCLUDE)
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies: []
created_at: 2026-06-12T15:27:12.137Z
updated_at: 2026-06-12T15:32:17.856Z
closed_at: 2026-06-12T15:32:17.856Z
close_reason: "Export surface settled: block-info types, SpanRef resolvers, block-tree fns, DEFAULT_INCLUDE, html_in_md siblings"
---
Review F2. Export CodeInfo/TableInfo/ListInfo, resolve/resolve_and_update, parse_blocks/walk_blocks/block_type_for from flexdoc.docs; html_p/html_tag/escape_attribute/tag_wrapper/identity_wrapper from flexdoc.html; rename _DEFAULT_INCLUDE->DEFAULT_INCLUDE and export. Keep IntervalIndex/node_table/render internals private.
