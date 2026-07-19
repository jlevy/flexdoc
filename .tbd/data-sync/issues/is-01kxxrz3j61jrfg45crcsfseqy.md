---
type: is
id: is-01kxxrz3j61jrfg45crcsfseqy
title: "PR #20 review S1: Reject non-canonical URI integers"
kind: bug
status: closed
priority: 3
version: 4
labels: []
dependencies: []
parent_id: is-01kxnwyc7hcd0djd3p2dknpj9k
created_at: 2026-07-19T18:07:13.478Z
updated_at: 2026-07-19T18:27:39.506Z
closed_at: 2026-07-19T18:27:39.506Z
close_reason: "Fixed in 16f3c07; PR #20 checks passed."
---
Formal review 4731209857 suggestion S1. src/flexdoc/docs/text_ref.py:717: reject leading-zero decimal positions in canonical TextRef URIs; add codec regression coverage.
