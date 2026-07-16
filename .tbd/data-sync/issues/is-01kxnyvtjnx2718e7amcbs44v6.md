---
type: is
id: is-01kxnyvtjnx2718e7amcbs44v6
title: "PR #20 review M3: Use explicit optional-boundary checks"
kind: bug
status: closed
priority: 3
version: 3
labels: []
dependencies: []
parent_id: is-01kxnwyc7hcd0djd3p2dknpj9k
created_at: 2026-07-16T17:16:21.972Z
updated_at: 2026-07-16T17:28:20.262Z
closed_at: 2026-07-16T17:28:20.262Z
close_reason: Fixed in 844298e with regression coverage and updated TextRef documentation.
---
PR #20 minor note. src/flexdoc/text_ref.py: replace integer-truthiness fallback for boundary_start with explicit None handling.
