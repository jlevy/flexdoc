---
type: is
id: is-01kxnyvrxrvsf3gb0m6hza9hvw
title: "PR #20 review R1: Preserve the typed DocGraph v0.1 return"
kind: bug
status: in_progress
priority: 1
version: 2
labels: []
dependencies: []
parent_id: is-01kxnwyc7hcd0djd3p2dknpj9k
created_at: 2026-07-16T17:16:20.279Z
updated_at: 2026-07-16T17:16:48.832Z
---
PR #20 finding 1. src/flexdoc/flex_doc.py: add overloads so graph() returns DocGraph when annotations is None and DocGraphV2 when an AnnotationSet is supplied; add a static type regression.
