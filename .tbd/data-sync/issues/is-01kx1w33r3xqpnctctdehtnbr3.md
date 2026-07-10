---
type: is
id: is-01kx1w33r3xqpnctctdehtnbr3
title: AI annotation/commenting workflow mechanisms
kind: feature
status: closed
priority: 2
version: 3
spec_path: docs/project/specs/active/plan-2026-07-08-post-review-refinements.md
labels: []
dependencies: []
created_at: 2026-07-08T22:03:06.370Z
updated_at: 2026-07-10T01:48:01.385Z
closed_at: 2026-07-10T01:48:01.384Z
close_reason: Superseded by the execution-ready Phase 2 epic flexdoc-6582 and its bounded child beads jl5b, rbvu, p6xv, hc17, zdu2, i229, vav2, and f4mz.
---
Minimal mechanism-shaped additions that unlock LLM commenting/review/chunking workflows (2026-07 review, section 6): (1) Annotation record type (SpanRef anchor + kind + body + attrs) typing DocGraph's reserved annotations slot, plus Detail.annotations; (2) SpanRef.from_quote(exact, source, ...) and resolve_batch(refs, source); (3) Section.text/own_text properties, FlexDoc.preamble_text, section_at_offset(offset); (4) section_outline() JSON skeleton (machine-readable section_size_tree); (5) SuggestedEdit type (SpanRef + replacement) for accept/reject edit loops; (6) tiered re-anchoring: exact -> whitespace/case-normalized -> fuzzy (fuzzy already tracked as flexdoc-z09f).
