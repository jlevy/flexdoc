---
type: is
id: is-01ktyc8dx19mf27b73v5zgxqj3
title: "Synthetic layer: migrate TextNode/parse_divs from chopdiff into the node table"
kind: feature
status: open
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels: []
dependencies: []
created_at: 2026-06-12T16:57:16.449Z
updated_at: 2026-07-10T00:57:05.317Z
---
Stage 4 of the extraction plan, now concretely mapped there: move chopdiff.divs (TextNode, parse_divs, chunk utils) into flexdoc and re-express marker-tag regions as synthetic-layer nodes keyed into the node table; builder pass over a configurable tag whitelist; partial-overlap fixtures (tags crossing block boundaries) and a LAYER_NESTING decision for non-nesting regions; divs tests migrate. Moderate difficulty; see plan Stage 4 for the step map.
