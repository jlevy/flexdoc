---
type: is
id: is-01kxxrvzpvwvmnn9gxybsaehq3
title: "PR #20 review R5: Use the TextRef format constant"
kind: bug
status: closed
priority: 3
version: 4
labels: []
dependencies: []
parent_id: is-01kxnwyc7hcd0djd3p2dknpj9k
created_at: 2026-07-19T18:05:31.226Z
updated_at: 2026-07-19T18:16:40.805Z
closed_at: 2026-07-19T18:16:40.805Z
close_reason: Fixed in b33bec0; local lint and 401 tests passed, and all required GitHub Actions checks passed.
---
Formal review PRR_kwDOS4aaIc8AAAABGgCIgQ, submitted 2026-07-19. src/flexdoc/docs/text_annotations.py:124: replace the hardcoded textref/0.1 literal with TEXTREF_FORMAT.
