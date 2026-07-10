---
type: is
id: is-01kx1w317zhc6zft6t2991msk3
title: Supply-chain refresh before promotion
kind: chore
status: open
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-07-08-post-review-refinements.md
labels: []
dependencies: []
created_at: 2026-07-08T22:03:03.807Z
updated_at: 2026-07-08T22:58:32.982Z
---
exclude-newer is 2026-05-11 (~58 days stale vs the 14-day policy). Bump to (today - 14d), remove the strif/flowmark/idna per-package overrides (all long past the window; SUPPLY-CHAIN-SECURITY.md says to remove them), run make upgrade, re-run pip-audit, and drop the PYSEC-2026-196 --ignore-vuln from ci.yml if it clears. Maintainer-gated per supply-chain policy. See docs/project/review/senior-engineering-review-flexdoc-2026-07.md section 4.
