---
type: is
id: is-01kxxrvyg4sc5knk9rwfe65j3g
title: "Future TextRef 0.2: bounded span evidence"
kind: bug
status: open
priority: 2
version: 4
labels: []
dependencies: []
parent_id: is-01kxnwyc7hcd0djd3p2dknpj9k
created_at: 2026-07-19T18:05:29.988Z
updated_at: 2026-07-19T18:17:39.632Z
---
Follow-up from formal review 4731209857 R1 after the textref/0.1 size tradeoff and fallback guidance were documented in b33bec0. Design a future bounded-evidence span selector, such as head/tail boundary context plus length and an exact digest, without changing the current textref/0.1 wire format.
