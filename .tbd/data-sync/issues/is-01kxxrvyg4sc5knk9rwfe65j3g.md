---
type: is
id: is-01kxxrvyg4sc5knk9rwfe65j3g
title: "Future TextRef 0.2: bounded span evidence"
kind: bug
status: closed
priority: 2
version: 5
labels: []
dependencies: []
parent_id: is-01kxnwyc7hcd0djd3p2dknpj9k
created_at: 2026-07-19T18:05:29.988Z
updated_at: 2026-07-19T18:27:39.492Z
closed_at: 2026-07-19T18:27:39.491Z
close_reason: "Fixed in 16f3c07; PR #20 checks passed."
---
Follow-up from formal review 4731209857 R1 after the textref/0.1 size tradeoff and fallback guidance were documented in b33bec0. Design a future bounded-evidence span selector, such as head/tail boundary context plus length and an exact digest, without changing the current textref/0.1 wire format.
