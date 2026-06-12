---
type: is
id: is-01kty73gk57xwfbfx2ydvh8p9d
title: Split text_doc.py into paragraphs/links/sections modules
kind: task
status: closed
priority: 2
version: 3
labels: []
dependencies: []
created_at: 2026-06-12T15:27:12.485Z
updated_at: 2026-06-12T15:40:10.843Z
closed_at: 2026-06-12T15:40:10.843Z
close_reason: text_doc.py split 1312->788 lines; paragraphs/links/sections modules; block_links promoted public; package surface unchanged
---
Review F4. Move Paragraph/Sentence/Offsets/SentIndex to paragraphs.py, Link+_block_links to links.py, Section to sections.py; text_doc.py keeps TextDoc + caching. flexdoc.docs package exports unchanged.
