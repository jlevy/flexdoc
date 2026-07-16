---
type: is
id: is-01kxnyvsn7szgqjahpc7h8a8k8
title: "PR #20 review R4: Cache TextRefContext snapshot indexes"
kind: bug
status: closed
priority: 2
version: 3
labels: []
dependencies: []
parent_id: is-01kxnwyc7hcd0djd3p2dknpj9k
created_at: 2026-07-16T17:16:21.030Z
updated_at: 2026-07-16T17:28:20.240Z
closed_at: 2026-07-16T17:28:20.240Z
close_reason: Fixed in 844298e with regression coverage and updated TextRef documentation.
---
PR #20 finding 4. src/flexdoc/text_ref_context.py and src/flexdoc/text_ref.py: reuse the bound source hash, lines, line starts, and structural ranges instead of recomputing document-wide state per annotation.
