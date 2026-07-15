---
type: is
id: is-01kx4v93df11zeqwtv429bbjfk
title: Implement typed exact TextRef resolution
kind: feature
status: closed
priority: 1
version: 9
spec_path: docs/project/specs/active/plan-2026-07-14-native-textref-integration.md
labels:
  - anchoring
  - release-0.4
  - textref
dependencies:
  - type: blocks
    target: is-01kx4v93vmm64a0ej1ar4fyth2
  - type: blocks
    target: is-01kx4v949qvnf289vy07ncj8a3
  - type: blocks
    target: is-01kxj3n1e7a7cbq6bf9ea7bzfn
parent_id: is-01kxj2kx1q8dnmyevecnmtka1r
created_at: 2026-07-10T01:46:37.358Z
updated_at: 2026-07-15T05:48:16.508Z
closed_at: 2026-07-15T05:48:16.506Z
close_reason: Implemented shared exact quote resolution, typed span/point/section outcomes, batch and quote construction APIs, compatibility coverage, and full validation.
---
Build the exact resolver shared by TextRef selectors and existing SpanRef behavior: add quote construction and batch resolution, typed document/source/selector/method outcomes, exact span recovery, point affinity and boundary handling, and semantic section resolution without arbitrary duplicate selection. Preserve SpanRef.resolve() compatibility. Done when unique, missing, ambiguous, stale-hint, Unicode, point, section, and mixed-batch cases have focused tests.
