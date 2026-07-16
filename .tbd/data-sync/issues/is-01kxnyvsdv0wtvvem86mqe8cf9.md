---
type: is
id: is-01kxnyvsdv0wtvvem86mqe8cf9
title: "PR #20 review R3: Optimize point context matching"
kind: bug
status: closed
priority: 2
version: 3
labels: []
dependencies: []
parent_id: is-01kxnwyc7hcd0djd3p2dknpj9k
created_at: 2026-07-16T17:16:20.795Z
updated_at: 2026-07-16T17:28:20.225Z
closed_at: 2026-07-16T17:28:20.225Z
close_reason: Fixed in 844298e with regression coverage and updated TextRef documentation.
---
PR #20 finding 3. src/flexdoc/text_ref.py: replace the Python boundary scan for point prefix/suffix matching with an equivalent occurrence search and preserve ambiguity behavior.
