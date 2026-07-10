---
type: is
id: is-01kx4r7w49xfwh8j9mn34qd9sh
title: "Reuse the shared parse for frontmatter link extraction (PR #9)"
kind: bug
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels: []
dependencies: []
parent_id: is-01kx4qtsc5g5kanpfhyh5j3kw0
created_at: 2026-07-10T00:53:31.400Z
updated_at: 2026-07-10T01:15:25.683Z
closed_at: 2026-07-10T01:15:25.682Z
close_reason: Shared frontmatter parse is reused; blanked source prevents repeated metadata URLs from stealing body spans; regressions pass.
---
src/flexdoc/docs/flex_doc.py reparses the body in _link_list() whenever frontmatter is present, contradicting the single-shared-parse contract and the design review claim that frontmatter blanking removes the asymmetry. Add a regression proving frontmatter documents parse once, then pass the blanked shared parse to block_links().
