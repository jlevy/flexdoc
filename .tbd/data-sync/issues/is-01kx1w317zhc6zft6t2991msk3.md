---
type: is
id: is-01kx1w317zhc6zft6t2991msk3
title: Supply-chain refresh before promotion
kind: chore
status: closed
priority: 1
version: 6
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - supply-chain
  - release-0.3
dependencies:
  - type: blocks
    target: is-01kx4v808gd28tns09r81qhs5q
parent_id: is-01kx4rdq9kt2dy2hzfc2c7fjdw
created_at: 2026-07-08T22:03:03.807Z
updated_at: 2026-07-10T02:10:33.605Z
closed_at: 2026-07-10T02:10:33.605Z
close_reason: Refreshed the project cutoff to 2026-06-26, removed all expired per-package exceptions, upgraded the reviewed lockfile without new dependencies, resolved pip 26.1.2 and msgpack 1.2.1, removed both CI audit ignores, and verified the unignored audit, lint, 343 tests, and GitHub CI in commit 8f8f04a.
---
Refresh exclude-newer to the reviewed 14-day cutoff, remove expired per-package overrides, update the lockfile under maintainer review, and rerun the unignored audit. Remove PYSEC-2026-196 and GHSA-6v7p-g79w-8964 suppressions if the eligible lock resolves fixed versions; otherwise record explicit maintainer ratification and removal conditions. Done when the documented supply-chain gate passes without an unratified exception.
