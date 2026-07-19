---
type: is
id: is-01kxxrvywczcn2qeeenf9xavbx
title: "PR #20 review R2: Preserve canonical LF line labels"
kind: bug
status: closed
priority: 3
version: 4
labels: []
dependencies: []
parent_id: is-01kxnwyc7hcd0djd3p2dknpj9k
created_at: 2026-07-19T18:05:30.378Z
updated_at: 2026-07-19T18:16:40.777Z
closed_at: 2026-07-19T18:16:40.776Z
close_reason: Fixed in b33bec0; local lint and 401 tests passed, and all required GitHub Actions checks passed.
---
Formal review PRR_kwDOS4aaIc8AAAABGgCIgQ, submitted 2026-07-19. src/flexdoc/docs/text_ref_context.py:502: split display lines only on LF so form feed, vertical tab, NEL, U+2028, and U+2029 remain content under the canonical source profile; add regression coverage.
