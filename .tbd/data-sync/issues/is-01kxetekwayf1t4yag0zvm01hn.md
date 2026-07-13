---
type: is
id: is-01kxetekwayf1t4yag0zvm01hn
title: Migrate TextUnit and all document sizing consumers
kind: task
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-13-logical-word-metrics.md
labels: []
dependencies:
  - type: blocks
    target: is-01kxetembq1w0mh10jmqx0nyn3
parent_id: is-01kxet6bt9hjzjwr4qvv2b83n7
created_at: 2026-07-13T22:44:33.801Z
updated_at: 2026-07-13T22:58:12.452Z
closed_at: 2026-07-13T22:58:12.451Z
close_reason: Migrated every document sizing grain and consumer from TextUnit.words to explicit raw_words/logical_words, switched defaults and reports to logical words, updated tests/examples/goldens, and prevented YAML scalar wrapping from adding trailing whitespace.
---
Replace TextUnit.words with raw_words and logical_words across Sentence, Paragraph, FlexDoc, Section, seek, summaries, debug output, and affected tests.
