---
type: is
id: is-01kxxrz4gt7gejakmhfzy0jdyr
title: "PR #20 review S5: Cover oversized URI render fallback"
kind: bug
status: closed
priority: 3
version: 3
labels: []
dependencies: []
parent_id: is-01kxnwyc7hcd0djd3p2dknpj9k
created_at: 2026-07-19T18:07:14.456Z
updated_at: 2026-07-19T18:16:40.822Z
closed_at: 2026-07-19T18:16:40.822Z
close_reason: Fixed in b33bec0; local lint and 401 tests passed, and all required GitHub Actions checks passed.
---
Formal review 4731209857 suggestion S5. Add a regression test proving render_context/render_annotations visibly fall back to structured TextRef when URI export exceeds its limit.
