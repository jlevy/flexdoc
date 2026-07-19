---
type: is
id: is-01kxxrvze0vj6jymq1dwvnvka0
title: "PR #20 review R4: Render invalid document resolution clearly"
kind: bug
status: closed
priority: 3
version: 4
labels: []
dependencies: []
parent_id: is-01kxnwyc7hcd0djd3p2dknpj9k
created_at: 2026-07-19T18:05:30.943Z
updated_at: 2026-07-19T18:16:40.794Z
closed_at: 2026-07-19T18:16:40.794Z
close_reason: Fixed in b33bec0; local lint and 401 tests passed, and all required GitHub Actions checks passed.
---
Formal review PRR_kwDOS4aaIc8AAAABGgCIgQ, submitted 2026-07-19. src/flexdoc/docs/text_ref.py:390 and annotation rendering: when document resolution is invalid, present that axis instead of the overloaded selector unsupported status; document selector-axis precedence and add regression coverage.
