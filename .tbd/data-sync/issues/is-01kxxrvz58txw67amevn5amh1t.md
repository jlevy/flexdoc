---
type: is
id: is-01kxxrvz58txw67amevn5amh1t
title: "PR #20 review R3: Give TextRefContext identity semantics"
kind: bug
status: closed
priority: 3
version: 4
labels: []
dependencies: []
parent_id: is-01kxnwyc7hcd0djd3p2dknpj9k
created_at: 2026-07-19T18:05:30.663Z
updated_at: 2026-07-19T18:16:40.788Z
closed_at: 2026-07-19T18:16:40.788Z
close_reason: Fixed in b33bec0; local lint and 401 tests passed, and all required GitHub Actions checks passed.
---
Formal review PRR_kwDOS4aaIc8AAAABGgCIgQ, submitted 2026-07-19. src/flexdoc/docs/text_ref_context.py:88: use dataclass frozen=True, eq=False so bound contexts compare and hash by identity instead of deep-comparing FlexDoc or raising on hash().
