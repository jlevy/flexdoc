---
type: is
id: is-01kxcrsccw5c6td9dvvgg5ca8k
title: Research Markdown diffs and redlines for TextRef
kind: task
status: closed
priority: 2
version: 4
spec_path: docs/project/research/research-2026-07-10-text-reference-microformat.md
labels:
  - documentation
  - research
dependencies: []
created_at: 2026-07-13T03:37:00.571Z
updated_at: 2026-07-13T04:03:50.656Z
closed_at: 2026-07-13T04:03:50.655Z
close_reason: Research brief updated and validated.
---
Research Markdown source diffs, inline redline syntaxes, and structured patch formats; determine whether TextRef or its annotation envelope needs first-class diff semantics and update the existing brief.

## Notes

Expanded the TextRef research brief with Markdown source-diff, rendered-diff, syntax-tree-diff, inline redline, typed edit proposal, and atomic change-set analysis. The design keeps TextRef operation-neutral, uses source hashes as automatic-application preconditions, treats redline syntaxes as directional adapters, and defers TextChangeSet until a consumer defines atomic semantics. Validation: target codespell and link/numbering audits pass; git diff --check passes; make test passes (354 tests). Repository make lint reached zero Ruff and BasedPyright errors but its codespell scope failed on pre-existing generated node_modules; tool-induced generated-file changes were restored.
