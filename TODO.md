# TODO

Open work, with the bead id tracking each item (`tbd show <id>` for details).
The extraction plan
([plan-2026-06-11-flexdoc-extraction.md](docs/project/specs/active/plan-2026-06-11-flexdoc-extraction.md))
has the full detail; this file is the summary.

## Open Work

- **Define the root-level public API surface** (`flexdoc-l0lc`, gates `flexdoc-bift`).
  Which symbols beyond `FlexDoc` belong at the package root.
  A concrete proposal (add `DocGraph`, `SpanRef`, `BlockType`, `NodeKind`, `Layer`,
  `TextUnit`; exclude unit types, wordtok/diff machinery, and html helpers) is pending
  maintainer review.
- **Implement the settled root surface** (`flexdoc-bift`; blocked by the above).
- **Synthetic layer: migrate `TextNode`/`parse_divs` from chopdiff into the node table**
  (`flexdoc-t5rh`). Concretely mapped in the extraction plan, Stage 4, including the
  open overlap-policy decision.
  Spec: `docs/flexdoc-spec.md` §3, §14.

## Release Steps

- Merge PR #1; configure the PyPI Trusted Publisher for `jlevy/flexdoc`; tag and publish
  `flexdoc 0.1.0` (extraction plan, Step 4).
- Rewire chopdiff to the published flexdoc — its intended breaking release, one-pass
  migration `chopdiff.docs.TextDoc` → `flexdoc.FlexDoc` (extraction plan, Step 5). Note:
  depending on freshly-published flexdoc needs a supply-chain cool-off exception in
  chopdiff (maintainer sign-off, like the strif/flowmark precedents).

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
