---
type: is
id: is-01kxxrz3tapscg0qfewk53tjxv
title: "PR #20 review S2: Validate embedded annotation bounds"
kind: bug
status: open
priority: 3
version: 3
labels: []
dependencies: []
parent_id: is-01kxnwyc7hcd0djd3p2dknpj9k
created_at: 2026-07-19T18:07:13.737Z
updated_at: 2026-07-19T18:18:01.527Z
---
Formal review 4731209857 suggestion S2. src/flexdoc/docs/doc_graph.py:142: when source.text is embedded, bounds-check annotation span start/end and point positions as well as node spans; add regression coverage.
