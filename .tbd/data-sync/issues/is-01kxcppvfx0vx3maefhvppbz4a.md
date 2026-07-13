---
type: is
id: is-01kxcppvfx0vx3maefhvppbz4a
title: Review markdown-review formats and anchoring design
kind: task
status: closed
priority: 2
version: 4
spec_path: docs/project/research/research-2026-07-10-text-reference-microformat.md
labels:
  - research
  - annotations
  - third-party
dependencies: []
created_at: 2026-07-13T03:00:40.572Z
updated_at: 2026-07-13T03:06:53.856Z
closed_at: 2026-07-13T03:06:53.855Z
close_reason: Reviewed markdown-review at pinned commit 149fe77, documented its internal state, target and export formats, added TextRef/annotation adapter guidance, and validated the repository with make lint and make test.
---
Check out rwoll/markdown-review to the attic using the tbd shortcut, review its source and persisted/transport formats, compare its anchoring model with TextRef and Plannotator, and update the text-reference research brief.

## Notes

Reviewed commit 149fe77c44645d16db4ba9689bde4952056404a6. Findings: annotations are in-memory Record<number,{note,time}> keyed by parsed element index; block mapping uses zero-based source start lines; no re-anchoring or persistence; feedback is Markdown and --json only wraps feedbackMarkdown; non-code comments omit source quotes; embedded question IDs are not validated unique/nonempty. Added design comparison and adapter guidance to the research brief.
