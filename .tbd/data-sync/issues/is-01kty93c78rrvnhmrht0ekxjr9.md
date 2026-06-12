---
type: is
id: is-01kty93c78rrvnhmrht0ekxjr9
title: Define the root-level public API surface (spec requirement)
kind: task
status: open
priority: 2
version: 2
labels: []
dependencies:
  - type: blocks
    target: is-01kty93chc0dmwfwm7z181sxd0
created_at: 2026-06-12T16:02:05.160Z
updated_at: 2026-06-12T16:02:18.984Z
---
Design task gating implementation: decide exactly which symbols belong at the flexdoc root beyond FlexDoc (candidates: DocGraph, collect, SpanRef, TextUnit, BlockType, NodeKind/Layer; criteria: needed in the first ten lines of typical use; no wordtok/diff internals at root). Deliverable: a Root API Surface requirement section in the extraction plan (or Stage 3 spec) listing the surface, criteria, and explicit exclusions, maintainer-approved.
