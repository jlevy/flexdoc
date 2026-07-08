# TODO

Open work, with the bead id tracking each item (`tbd show <id>` for details).
The extraction plan
([plan-2026-06-11-flexdoc-extraction.md](docs/project/specs/active/plan-2026-06-11-flexdoc-extraction.md))
has the full detail; this file is the summary.

## Open Work

- **Synthetic layer: migrate `TextNode`/`parse_divs` from chopdiff into the node table**
  (`flexdoc-t5rh`). Concretely mapped in the extraction plan, Stage 4, including the
  open overlap-policy decision.
  Spec: `docs/flexdoc-spec.md` §3, §14.
- **Supply-chain refresh before promotion** (`flexdoc-pcac`): bump the stale
  `exclude-newer` cutoff, drop the expired per-package overrides, re-lock, and clear
  the pip-audit ignore if it no longer applies.
- **Pre-1.0 API design decisions** (`flexdoc-lcuh`): the batch of cheap-now breaking
  cleanups from the 2026-07 review
  (`docs/project/review/senior-engineering-review-flexdoc-2026-07.md` §5).
- **AI annotation/commenting workflow mechanisms** (`flexdoc-86iy`): `Annotation`
  record type for the reserved DocGraph slot, `SpanRef.from_quote`/`resolve_batch`,
  `Section.text`/`section_outline()`/`section_at_offset` (review §6).

## Downstream Work (in chopdiff, not this repo)

0.1.0 and 0.2.0 are published to PyPI with tags `v0.1.0`/`v0.2.0` (extraction plan,
Step 4 — done). Remaining:

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
