---
type: is
id: is-01kx1w317zhc6zft6t2991msk3
title: Supply-chain refresh before promotion
kind: chore
status: open
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - supply-chain
  - release-0.3
dependencies:
  - type: blocks
    target: is-01kx4v808gd28tns09r81qhs5q
parent_id: is-01kx4rdq9kt2dy2hzfc2c7fjdw
created_at: 2026-07-08T22:03:03.807Z
updated_at: 2026-07-10T01:47:39.582Z
---
Refresh exclude-newer to the reviewed 14-day cutoff, remove expired per-package overrides, update the lockfile under maintainer review, and rerun the unignored audit. Remove PYSEC-2026-196 and GHSA-6v7p-g79w-8964 suppressions if the eligible lock resolves fixed versions; otherwise record explicit maintainer ratification and removal conditions. Done when the documented supply-chain gate passes without an unratified exception.
