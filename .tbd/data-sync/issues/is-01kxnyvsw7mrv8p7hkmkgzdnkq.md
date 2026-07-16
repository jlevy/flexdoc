---
type: is
id: is-01kxnyvsw7mrv8p7hkmkgzdnkq
title: "PR #20 review R5: Specify context-free point references"
kind: bug
status: closed
priority: 2
version: 4
labels: []
dependencies: []
parent_id: is-01kxnwyc7hcd0djd3p2dknpj9k
created_at: 2026-07-16T17:16:21.254Z
updated_at: 2026-07-16T17:28:20.245Z
closed_at: 2026-07-16T17:28:20.245Z
close_reason: Fixed in 844298e with regression coverage and updated TextRef documentation.
---
PR #20 finding 5. Document that context-free points are reserved for hash-bound document start, add a regression proving a mismatched hash cannot resolve without context, and explain the rationale in the spec, plan, and usage guide.
