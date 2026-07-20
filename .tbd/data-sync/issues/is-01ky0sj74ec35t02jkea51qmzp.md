---
type: is
id: is-01ky0sj74ec35t02jkea51qmzp
title: Validate packaging and release gates
kind: task
status: in_progress
priority: 1
version: 3
labels:
  - release
dependencies: []
parent_id: is-01ky0shwff93nvgk9zfd5jb1y6
created_at: 2026-07-20T22:15:23.021Z
updated_at: 2026-07-20T22:34:44.480Z
---
Run lint, type checking, the full test suite, package build/install smoke tests, supply-chain audit, and inspect release workflow and metadata.

## Notes

Candidate gates pass locally: codespell/Ruff/format/BasedPyright clean with 0 errors and warnings; 407 pytest tests pass on Python 3.14; pip-audit reports no known vulnerabilities; wheel builds and installs in isolation; public TextRef imports, resolution, and packaged JSON schemas pass smoke validation. Main commit CI was already green across Python 3.11-3.14, macOS, audit, and wheel smoke; branch PR CI remains to be run.
