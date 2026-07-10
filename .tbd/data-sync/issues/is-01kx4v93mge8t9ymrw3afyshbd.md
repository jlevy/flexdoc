---
type: is
id: is-01kx4v93mge8t9ymrw3afyshbd
title: Add structural text accessors and section outlines
kind: feature
status: open
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - structure
  - release-0.4
dependencies:
  - type: blocks
    target: is-01kx4v949qvnf289vy07ncj8a3
parent_id: is-01kx4re3wmzeh04vavf8fz5fst
created_at: 2026-07-10T01:46:37.583Z
updated_at: 2026-07-10T01:47:42.017Z
---
Add Section.text, Section.own_text, FlexDoc.preamble_text, section_at_offset, and a JSON-serializable section_outline. Done when headingless preambles, nested sections, boundary offsets, size data, serialization, and source-slice invariants are covered without duplicating existing tree logic.
