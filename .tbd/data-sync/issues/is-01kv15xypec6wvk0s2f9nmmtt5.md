---
type: is
id: is-01kv15xypec6wvk0s2f9nmmtt5
title: Add Link.form discriminator and surface reference definitions
kind: feature
status: closed
priority: 2
version: 5
spec_path: docs/project/specs/active/plan-2026-06-13-metrics-use-case.md
labels: []
dependencies:
  - type: blocks
    target: is-01kv15xzjc48nfvznpbmfbzh3d
  - type: blocks
    target: is-01kv17dwymds7tcmxcwxbfjddz
created_at: 2026-06-13T19:04:25.038Z
updated_at: 2026-06-13T20:16:54.499Z
closed_at: 2026-06-13T20:16:54.499Z
close_reason: null
---
API gap 3 / #5. LinkForm enum (inline/autolink/bare_url/reference/image/reference_definition) + required Link.form classified in block_links. Surface marko Document.link_ref_defs as Link(form=reference_definition) and NodeKind.link_ref_def nodes. Link nodes carry form in node table.
