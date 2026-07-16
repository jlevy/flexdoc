---
type: is
id: is-01kxp0hjtg13jpbafaapmyp7m4
title: Unify DocGraph and specify TextRef integration end to end
kind: feature
status: closed
priority: 1
version: 6
spec_path: docs/flexdoc-spec.md
labels: []
dependencies: []
parent_id: is-01kxnwyc7hcd0djd3p2dknpj9k
child_order_hints:
  - is-01kxp0hwqy04jjwt9gj5q9jsmb
  - is-01kxp0hx1bqwnt5nr73qx1cszp
  - is-01kxp0hx9mn52c3gkbgbknpk1z
created_at: 2026-07-16T17:45:43.501Z
updated_at: 2026-07-16T18:05:44.781Z
closed_at: 2026-07-16T18:05:44.781Z
close_reason: Unified DocGraph into one source-identifying v0.2 contract, rewrote the TextRef specification from first principles, aligned all APIs and artifacts, and verified local and CI checks.
---
Remove the compatibility-driven DocGraph/DocGraphV2 split. Define one self-contained DocGraph contract with document identity, source hash, optional embedded annotations, and a direct mapping from source spans to TextRefs. Rewrite the authoritative FlexDoc spec so TextRef construction, serialization, resolution, context rendering, annotations, and DocGraph composition are understandable from first principles.
