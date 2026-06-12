---
type: is
id: is-01kty93bx4jfccnnh5z9gnymka
title: "Root import: from flexdoc import FlexDoc"
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies: []
created_at: 2026-06-12T16:02:04.835Z
updated_at: 2026-06-12T16:08:56.850Z
closed_at: 2026-06-12T16:08:56.850Z
close_reason: from flexdoc import FlexDoc root export; __init__ docstring rewritten; README root-import example; ci wheel-smoke + tests/test_root_api.py pin identity and exact __all__
---
Export FlexDoc (the primary entry point) from the package root; rewrite flexdoc/__init__ docstring (root carries the entry point; submodules carry the full surfaces); README example uses the root import; contract test pinning root export identity. Amends the earlier submodule-only stance by maintainer decision; full root surface definition tracked separately.
