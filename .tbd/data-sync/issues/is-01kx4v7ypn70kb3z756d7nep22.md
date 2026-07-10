---
type: is
id: is-01kx4v7ypn70kb3z756d7nep22
title: Rename the navigable-link form constant
kind: task
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md
labels:
  - api
  - release-0.3
dependencies:
  - type: blocks
    target: is-01kx4v808gd28tns09r81qhs5q
parent_id: is-01kx1w32h8f8920d8kp9xh8ngc
created_at: 2026-07-10T01:45:59.764Z
updated_at: 2026-07-10T02:41:25.514Z
closed_at: 2026-07-10T02:41:25.513Z
close_reason: "Renamed TRUE_LINK_FORMS to NAVIGABLE_LINK_FORMS without an alias in cd07493, migrated internal consumers, package export, golden invariant, specs and changelog, make lint passed, all 348 tests passed, and PR #10 CI passed."
---
Rename TRUE_LINK_FORMS to NAVIGABLE_LINK_FORMS without a compatibility alias under the pre-1.0 policy. Done when internal imports, tests, user docs, exports, and the migration changelog use the new name and no stale references remain.
