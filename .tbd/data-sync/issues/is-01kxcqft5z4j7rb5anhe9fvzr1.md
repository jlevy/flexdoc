---
type: is
id: is-01kxcqft5z4j7rb5anhe9fvzr1
title: Research closed-source Markdown annotation tool from Reddit
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
created_at: 2026-07-13T03:14:18.431Z
updated_at: 2026-07-13T03:21:55.973Z
closed_at: 2026-07-13T03:21:55.972Z
close_reason: Investigated Remark from public product artifacts and its checksum-verified signed 2026.4.0 distribution, documented the observable CLI/MCP JSON contract and review workflow with uncertainty boundaries, integrated design lessons into the TextRef brief, and validated with make lint and make test.
---
Investigate the Markdown annotation tool described in the linked ClaudeAI Reddit post using public artifacts, determine any observable persisted/export formats and useful workflows, distinguish confirmed behavior from inference, and update the text-reference research brief.

## Notes

Investigated Remark from the linked Reddit post. Public launch post (2026-02-24) described remark export/resolve, JSON with location/context, a Claude skill, partial matching, and a Rust backend. Current product/release 2026.4.0 uses a Swift app, local bearer-token MCP server, CLI/stdio proxy, folder review, status filters, orphaning, and history. Public cask at ebb3abd confirms private source and bundled CLI. Checksum-verified signed distribution matched cask SHA-256 and was statically inspected without launch or license bypass; bundled intended skill exposes list_comments, set_comment_status, export_review. Observable model separates workflow status unresolved/needs_clarification/fixed from anchor state anchored/relocated/orphaned, and exposes active_anchor, last_known_anchor, history, UTF-16 offsets, selected text, source lines/columns, matcher exact_offset/exact_context/fuzzy/manual, confidence, content_sha256, and actor events. Exact JSON nesting, hash normalization, bases, and fuzzy thresholds remain undocumented. Updated brief with workflow, evidence levels, adapter mapping, anchor-history and state-separation recommendations.
