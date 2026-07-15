---
type: is
id: is-01kxj0e66k42y9wf7znd7f52sd
title: Add optional canonical DocGraph tree view to inspector
kind: feature
status: closed
priority: 2
version: 4
labels: []
dependencies: []
created_at: 2026-07-15T04:26:54.546Z
updated_at: 2026-07-15T04:37:14.286Z
closed_at: 2026-07-15T04:37:14.285Z
close_reason: "Added and validated the optional layered DocGraph inspector view in PR #17."
---

## Notes

Implemented optional mutually exclusive Markdown/DocGraph inspector pane. DocGraph view uses exported parent/children links, displays declared layer nesting guarantees, renders document and Markdown trees plus ordered textual paragraph/sentence hierarchy, and synchronizes the active path without page scrolling. Full Python and Bun checks pass.
