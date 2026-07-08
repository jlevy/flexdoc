---
type: is
id: is-01kx1w32h8f8920d8kp9xh8ngc
title: Pre-1.0 API design decisions (from 2026-07 review)
kind: task
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-07-08T22:03:05.128Z
updated_at: 2026-07-08T22:03:05.128Z
---
Batch of breaking-but-cheap-now decisions: (1) TextUnit -> StrEnum (matches every other enum); (2) collect(recursive=True) should arguably imply inline=True; (3) Section/Block mutability vs cache sharing (freeze or deepcopy); (4) Paragraph.heading_level()/heading_title() methods -> properties (Block's are properties); (5) rename TRUE_LINK_FORMS -> NAVIGABLE_LINK_FORMS; (6) tier flexdoc.docs exports (26 wordtok symbols dilute the surface); (7) export resolve/resolve_and_update from root or add SpanRef.resolve(); (8) frontmatter delimiter trailing-whitespace tolerance; (9) Section.size() throwaway FlexDoc refactor. Details + recommendations: docs/project/review/senior-engineering-review-flexdoc-2026-07.md section 5.
