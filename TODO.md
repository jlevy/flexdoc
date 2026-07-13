# TODO

Open work, with the bead id tracking each item (`tbd show <id>` for details).
The extraction plan
([plan-2026-06-11-flexdoc-extraction.md](docs/project/specs/active/plan-2026-06-11-flexdoc-extraction.md))
has the full detail; this file is the summary.

## Open Work

- **Cross-language logical word metrics:** replace the ambiguous `TextUnit.words` with
  explicit raw and logical measures, migrate default summaries and token estimates,
  and document the pre-1.0 API break. Epic: `flexdoc-2u8z`; GitHub issue #16; spec:
  [plan-2026-07-13-logical-word-metrics.md](docs/project/specs/active/plan-2026-07-13-logical-word-metrics.md).
- **Synthetic layer: migrate `TextNode`/`parse_divs` from chopdiff into the node table**
  (`flexdoc-t5rh`). Concretely mapped in the extraction plan, Stage 4, including the
  open overlap-policy decision.
  Spec: `docs/flexdoc-spec.md` §3, §14.
- **Stabilization and promotion roadmap:** the 2026-07 review’s open decisions and
  future mechanisms are consolidated in
  [plan-2026-07-09-flexdoc-stabilization-roadmap.md](docs/project/specs/active/plan-2026-07-09-flexdoc-stabilization-roadmap.md).
  Epic: `flexdoc-aqjg`; Phase 1 (`flexdoc-r634`, the 0.3.0 contract and release) is
  complete with 0.3.0 published 2026-07-11, leaving `flexdoc-6582` (source-grounded
  workflow APIs and 0.4.0) and `flexdoc-ww1i` (extensions, downstream adoption, and
  promotion).

## Downstream Work (in Chopdiff, Not This Repo)

0.1.0 through 0.3.0 are published to PyPI with tags `v0.1.0`/`v0.2.0`/`v0.3.0`
(extraction plan, Step 4, done). Remaining:

- Rewire Chopdiff to the published FlexDoc release in one breaking migration from
  `chopdiff.docs.TextDoc` to `flexdoc.FlexDoc` (extraction plan, Step 5). Depending on a
  newly published FlexDoc version requires Chopdiff’s supply-chain cool-off or an
  explicit maintainer-approved exception.

## Deferred (Specified, Not Yet Built; Spec §14)

- Annotation layer; cross-layer structural edits; fuzzy `SpanRef` re-anchoring;
  operation/provenance/layout layers (schema-reserved).
- A uniform opt-in strict-validation/diagnostics pass over a parse (spec §2, Error
  posture).
- Swap the hand-rolled frontmatter parser for `frontmatter-format`’s string API once it
  is released upstream (blocked on the upstream naming decision and a cool-off
  exception).
- Revisit `token_diffs` placement; a couple more flexdoc-specific runnable examples;
  rename `tests/html/test_html_validation_and_classes.py` (minor, from Stage 5).

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
