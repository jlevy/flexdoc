---
type: is
id: is-01kxxrz3j61jrfg45crcsfseqy
title: "PR #20 review S1: Reject non-canonical URI integers"
kind: bug
status: open
priority: 3
version: 3
labels: []
dependencies: []
parent_id: is-01kxnwyc7hcd0djd3p2dknpj9k
created_at: 2026-07-19T18:07:13.478Z
updated_at: 2026-07-19T18:18:01.312Z
---
Formal review 4731209857 suggestion S1. src/flexdoc/docs/text_ref.py:717: reject leading-zero decimal positions in canonical TextRef URIs; add codec regression coverage.
