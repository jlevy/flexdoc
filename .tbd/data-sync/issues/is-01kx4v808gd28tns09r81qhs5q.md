---
type: is
id: is-01kx4v808gd28tns09r81qhs5q
title: Validate and publish FlexDoc 0.3.0
kind: task
status: open
priority: 1
version: 9
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - release
  - release-0.3
dependencies:
  - type: blocks
    target: is-01kx4v936azv1s1t8hbxq50gdt
  - type: blocks
    target: is-01kx4v93df11zeqwtv429bbjfk
  - type: blocks
    target: is-01kx4v93mge8t9ymrw3afyshbd
  - type: blocks
    target: is-01kx4scz7fg18c4zan1vexkscb
  - type: blocks
    target: is-01kx4v942qgm3dv729zbwzyxvc
  - type: blocks
    target: is-01ktyc8dx19mf27b73v5zgxqj3
  - type: blocks
    target: is-01kx4re3wmzeh04vavf8fz5fst
  - type: blocks
    target: is-01kx4re3wcn6vvzsn36nqw37fd
parent_id: is-01kx4rdq9kt2dy2hzfc2c7fjdw
created_at: 2026-07-10T01:46:01.359Z
updated_at: 2026-07-10T01:51:32.084Z
---
Phase 1 gate. Review every breaking change and migration note, run lint, the full suite, golden regeneration, wheel smoke, and the security audit under the ratified policy, then publish 0.3.0 through the tag-driven workflow. Done when the released artifact installs cleanly and reports the expected public surface and version.
