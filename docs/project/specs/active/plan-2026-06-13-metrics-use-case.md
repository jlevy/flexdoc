# Feature: Document-Metrics Use Case — `node_table` crash, `sections()`/`toc()` heading loss, and inline/heading/link API completion

**Date:** 2026-06-13 (last updated 2026-06-13)

**Author:** Joshua Levy

**Status:** Draft

## Overview

[pprose](https://github.com/jlevy/practical-prose) is retiring its hand-rolled
regex metrics (`metrics.py`) in favor of flexdoc's typed document model. Migrating
against flexdoc 0.1.0 surfaced two correctness bugs and a cluster of API gaps,
filed together as [#6](https://github.com/jlevy/flexdoc/issues/6) (link-form gaps
recapped from [#5](https://github.com/jlevy/flexdoc/issues/5)). This plan lands all
of them in one cleanup release, **0.1.1**.

Two of the items are bugs where the model violates its own documented contract:
`collect()`/`node_table()`/`graph()` raise on valid Markdown (against P17 and the
node table's own builder-vs-input contract), and `sections()`/`toc()` lose headings
that `blocks()` finds (against spec §7, which already states sections derive from the
structural heading set). The rest complete the typed surface the metrics use case
needs — heading level on the authoritative heading set, a link-form discriminator
with reference-definition surfacing, and a prose-only text projection for editorial
linting — plus two small ergonomic gaps from #5.

This is a **clean-design** release, not a compatibility-constrained one. flexdoc 0.1.0
is a preview; nothing downstream is required to be preserved, so signatures are revised
wherever a clearer shape exists (e.g. `Link` gains a required `form`; `collect()`'s
inline ergonomics are fixed rather than worked around). The guiding constraint is the
spec's design language (single source of truth, parser-authoritative metadata, lenient
input / strict internal contracts), not source-level compatibility.

## Goals

- **`collect()` / `node_table()` / `graph()` never raise on valid Markdown** (P17;
  node-table builder contract). Inline extraction is scoped so an inline node can
  never cross a block boundary.
- **`sections()` / `toc()` recover every heading `blocks()` finds**, with per-heading
  level and title, derived from the structural heading set exactly as spec §7 already
  specifies.
- **Heading level is first-class on the structural `Block`** (parser-authoritative
  `HeadingInfo`), mirroring `CodeInfo`/`TableInfo`/`ListInfo`, and becomes the single
  source the node table reads (retiring the hand-rolled `#`-counting in `node_table.py`).
- **Links carry a typed `form`** (`inline` / `autolink` / `bare_url` / `reference` /
  `image` / `reference_definition`), and **reference definitions are surfaced** as a
  typed node kind, so the metrics breakdown needs no heuristics.
- **A prose-only text projection** that excludes frontmatter, code, and tables *and*
  strips inline code/links — the text editorial linting actually wants.
- **Close the two small #5 ergonomic gaps**: `block_at_offset` (offset→block inversion)
  and the `collect(kinds={inline})`-without-`recursive` footgun.

## Non-Goals

- **Fuzzy / edit-distance `SpanRef` re-anchoring** (#5 item 4, spec §14) — forward-looking,
  stays deferred.
- **The synthetic layer** (`flexdoc-t5rh`, `TextNode`/`parse_divs`) — unrelated, stays
  on its own track.
- **A uniform opt-in strict-validation / diagnostics pass** (spec §2, §14) — out of scope.
- **Typing pprose's editorial lint heuristics** (banned register, em-dash discipline) —
  #5 records these as out of scope for flexdoc; the prose-text projection is the only
  support flexdoc owes them.

## Background

All repros below are from the issue and verified against the source on branch
`claude/compassionate-mayer-3zwwrj`.

### Bug 1 — `node_table()` raises on valid Markdown

```python
from flexdoc import FlexDoc
from flexdoc.docs.node import NodeKind
src = "```python\n```\n  a `` ```t `` b\n- Inline `Emphasis` text\n"
FlexDoc.from_text(src).collect(kinds={NodeKind.image}, recursive=True)
# ValueError: layer nesting violated: markdown node n0011 span (27, 41)
#             not within parent n0002 span (16, 30)
```

`node_table._build_inline_nodes` discovers inline atomic spans over the **whole**
`source_text` via `flowmark.atomic_spans.iter_atomic_spans`, then parents each inline
node with `index.innermost(span[0], Layer.markdown)` — using only the span **start**.
Global backtick pairing produces an inline span that straddles a block boundary; its
end exceeds the start-chosen parent block, and `_validate_layer_nesting` raises. The
validator is correct (a builder invariant, never input validation — its own docstring
says "malformed Markdown must still build (P17)"); the **builder** is at fault for
discovering spans globally rather than per block. Because `collect()`/`node_table()`/
`graph()` are the only typed path to inline elements, this blocks all inline-element
access on the affected inputs (2 of 61 real docs in pprose).

### Bug 2 — `sections()` / `toc()` drop headings `blocks()` finds

```python
from flexdoc import FlexDoc
from flexdoc.docs.block_types import BlockType
for src in ["\n## Heading\n\nbody\n", "# A\nintro\n## B\nbody\n"]:
    d = FlexDoc.from_text(src)
    n = sum(1 for b in d.blocks() if b.type == BlockType.heading)
    print(n, len(d.toc()))   # blocks finds the headings; toc drops them
```

`flex_doc._section_list` walks `self.paragraphs` and recognizes a heading only when a
blank-line **paragraph**'s `heading_level()` is non-`None` — i.e. the heading must be
the paragraph's first line. Two triggers lose headings: **tight formatting** (no blank
line before the next heading merges heading + body into one paragraph) and a
**non-blank line immediately above** the heading (e.g. an HTML-comment marker), which
lands the heading mid-paragraph. This contradicts spec §7, which already says: *"What
starts a section: exactly the top-level structural `heading` blocks of `blocks()`."*
The implementation re-derives headings from the editing view instead. Scope: 4 of 61
pprose docs, including `AGENTS.md` (3 of 4 headings lost, each `##` preceded by a
`<!-- ... -->` marker with no blank line).

### API gaps (from #6 / #5)

- **Heading level on the authoritative set.** `Block` exposes no level; today it is
  reachable only via the node table (Bug 1) or by re-parsing source.
- **Link-form discrimination + reference definitions.** `links()` collapses inline /
  autolink / bare-URL / reference-use into one `link` with `{url, text}`, returns bare
  URLs as links, and never surfaces `[id]: url` definitions (marko resolves them away).
- **Prose-only text.** `filtered(include=...)` filters by block type but keeps inline
  code/links inside paragraphs, and `reassemble()` normalizes whitespace (changing
  `" — "` and link counts). pprose keeps a regex strip for this.

## Design

### Approach

Two correctness fixes first (Phase 1), then the typed-surface completion (Phase 2),
shipped together as 0.1.1. Each fix is grounded in the existing design rather than a
bolt-on: Bug 1 is fixed structurally by scoping inline discovery to block spans; Bug 2
is fixed by making the implementation match spec §7; heading metadata follows the
established `*_info` pattern; link forms extend the existing `Link`/`block_links` path.

### Components

**Phase 1 — correctness.**

1. **Inline extraction scoped per block** (`node_table._build_inline_nodes`).
   Replace the global `iter_atomic_spans(source_text)` pass with a per-block scan:
   iterate the markdown-layer **leaf content blocks** (block nodes with no
   markdown-block children, excluding `code`), and for each run
   `iter_atomic_spans(source_text[start:end])`, shift spans by `start`, and parent the
   resulting inline nodes to that block. Backtick pairing is then per block, so an
   inline node's span is always within its parent — fixing the crash structurally and
   making "inline access cannot crash" (#6 need 2) a structural guarantee, not a guard.
   Links keep `doc.links()` (cross-block reference resolution) but are parented by
   **full containment** — the innermost markdown block whose span contains the *entire*
   link span — instead of by start offset; a link contained by no block attaches to no
   parent rather than crashing (defensive; should not occur for real inline links).
   `_validate_layer_nesting` is unchanged — the strict internal contract stays; the
   builder now honors it.

2. **`HeadingInfo` on `Block`** (`block_info.py`, `block_tree.py`, `node_table.py`).
   Add `HeadingInfo(level: int, title: str)` and `heading_info_for(element)` —
   parser-authoritative from marko `Heading.level` / `SetextHeading.level` and the
   element's inline text — mirroring `CodeInfo`/`TableInfo`/`ListInfo`. Carry
   `Block.heading_info: HeadingInfo | None` (`compare=False, repr=False`, like the
   other infos) with a `Block.heading_level: int | None` convenience. `node_table.
   _build_markdown_nodes` reads `block.heading_info.level` for `attrs["level"]`,
   retiring the hand-rolled `#`-counting and setext detection (`node_table.py:81–100`).
   This is the single source for Bug 2's level/title too.

3. **`sections()` / `toc()` from the structural heading set** (`flex_doc._section_list`,
   `sections.Section`). Rewrite `_section_list` to iterate the **top-level structural
   `heading` blocks** of `blocks()` (not the paragraph view), taking level + title from
   each block's `HeadingInfo` and position from its span, and building the tree with the
   existing stack-by-level semantics (spec §7 ownership/nesting/preamble rules
   unchanged).
   - `Section.heading`: reuse the coinciding blank-line `Paragraph` when one starts at
     the heading block's start (the well-formed common case — byte-identical to today);
     otherwise synthesize a `Paragraph` from the heading block's exact source slice
     (glued / marker-preceded case). A deterministic, documented behavior (P17).
   - `Section.content`: assign each non-heading blank-line paragraph to the innermost
     section whose span contains the paragraph's start; preamble paragraphs (before the
     first heading) belong to no section. Equivalent to today for well-formed docs;
     degrades visibly for pathological glued docs (a single paragraph holding a heading
     plus body counts under that heading's section).
   Result: `len(toc()) == #{top-level heading blocks} == sections heading count` on all
   inputs.

**Phase 2 — typed surface for metrics.**

4. **Link `form` + reference definitions** (`links.py`, `node.py`, `node_table.py`,
   `collect.py`). Add `LinkForm` (`StrEnum`: `inline`, `autolink`, `bare_url`,
   `reference`, `image`, `reference_definition`) and a required `Link.form`. `block_links`
   classifies each identity from how it was located: `inline` (a `markdown_link` atomic
   containing `](`), `reference` (a `markdown_link` resolved by text, with the URL in a
   separate definition), `autolink` (located with surrounding `<>`), `bare_url` (located
   as a verbatim URL with no brackets). Reference definitions come parser-authoritatively
   from marko's `Document.link_ref_defs` (`{id: (url, title)}`); spans are recovered by
   locating the `[id]:` line in source. They are surfaced as `Link(form=reference_definition)`
   in `links()` **and** as `NodeKind.link_ref_def` nodes in the node table (so
   `collect(kinds={NodeKind.link_ref_def})` counts them) — #5 accepts either; doing both
   is cheap and consistent. Images stay surfaced via the node-table atomic pass with
   `NodeKind.image`; whether `links()` should also include them with `form=image` is an
   open question (see below).

5. **Prose-text projection** (`flex_doc.prose_text()`). A method returning prose-only
   text for editorial linting: take prose-bearing blocks (`paragraph`, `heading`;
   exclude `code`, `table`, `html`, `thematic_break`, and frontmatter), use each block's
   **verbatim source slice** (not `reassemble()`, to preserve `" — "` spacing), and strip
   inline non-prose spans via the node table — inline `code_span` removed, `link`/`image`
   replaced by their text, `inline_html` / `footnote_ref` removed — joining blocks with
   blank lines. Depends on Bug 1 being fixed (uses the node table). Default replacement
   policy above; flagged as an open question, with a documented `collect()` recipe as the
   fallback if the contract proves contentious (#6 need 4 accepts "or documented recipe").

6. **Ergonomics** (`flex_doc.py`, `collect.py`). `FlexDoc.block_at_offset(offset) ->
   Block | None` — the innermost structural block whose span contains `offset`,
   completing the inversion set beside `paragraph_at_offset` / `sentence_at_offset` (#5
   item 3). And fix `collect()` so requesting inline kinds (explicit inline `kinds`, or
   `inline=True`) widens the candidate set to all nodes, so `collect(kinds={NodeKind.link})`
   works without `recursive=True` (#5 ergonomics note) — the current root-only default
   silently returns `[]`.

### API Changes

- `Block`: new `heading_info: HeadingInfo | None` field + `heading_level: int | None`
  property. New `HeadingInfo` and `heading_info_for` in `flexdoc.docs.block_info`
  (exported from `flexdoc.docs`).
- `Link`: new required `form: LinkForm` field; new `LinkForm` enum (exported from
  `flexdoc.docs`). `links()` now includes `reference_definition` entries.
- `NodeKind`: new `link_ref_def` member (a new kind in the cross-language `DocGraph`
  contract; any port must learn it).
- `FlexDoc`: new `prose_text()` and `block_at_offset()` methods.
- `collect()`: inline-kind requests no longer require `recursive=True`.
- `node_table`: inline nodes scoped per block; markdown heading `level` sourced from
  `HeadingInfo`; new `link_ref_def` nodes; link nodes carry `form`.

## Implementation Plan

### Phase 1: Correctness — crash and heading loss

- [ ] `HeadingInfo` + `heading_info_for` in `block_info.py` (with inline tests); carry
      `heading_info` and `heading_level` on `Block`; populate in `block_tree._blocks_from`.
- [ ] `node_table._build_markdown_nodes` reads `block.heading_info` for `attrs["level"]`;
      remove the `#`-counting/setext scan.
- [ ] Scope `node_table._build_inline_nodes` inline discovery per leaf content block;
      parent links by full containment; keep `_validate_layer_nesting` intact.
- [ ] Rewrite `flex_doc._section_list` to derive sections from top-level heading blocks;
      reuse/synthesize `Section.heading`; assign `content` by offset.
- [ ] Regression tests: Bug 1 repro asserts no raise + correct inline nodes; Bug 2 repros
      assert `len(toc()) == #heading blocks` (tight and marker-preceded cases).
- [ ] Golden corpus: add a backtick-straddling/empty-fence doc and a tight +
      marker-preceded-heading doc; add a `test_model_invariants` check that `len(toc())`
      equals the top-level heading-block count and every inline node's span ⊆ its parent.
      Regenerate goldens (`UPDATE_GOLDEN=1`) and review the diff.

### Phase 2: Typed surface — links, prose text, ergonomics

- [ ] `LinkForm` + `Link.form`; classify forms in `block_links`; surface
      `reference_definition` from `Document.link_ref_defs` with recovered spans.
- [ ] `NodeKind.link_ref_def`; emit ref-def nodes and `form` on link nodes in
      `node_table`; export `LinkForm`; per-form tests including bare-URL vs autolink.
- [ ] `FlexDoc.prose_text()` (node-table-backed strip); tests for inline-code/link
      stripping and `" — "` preservation.
- [ ] `FlexDoc.block_at_offset()`; `collect()` inline-without-`recursive` fix; tests.
- [ ] `CHANGELOG.md` 0.1.1 section (Fixed: Bug 1, Bug 2; Added: heading level on `Block`,
      `LinkForm`/`Link.form` + reference-definition surfacing/`link_ref_def`,
      `prose_text()`, `block_at_offset()`, `collect()` inline ergonomics). Update
      `TODO.md` / spec references; tag `v0.1.1` per `docs/publishing.md`; close #6 (and
      the folded-in #5 items).

## Testing Strategy

- **Regression-first**: the issue's minimal repros become tests under `tests/docs/`
  (`test_node_table.py`, `test_sections.py`), each asserting the contract the bug broke.
- **Golden corpus** (`tests/golden/`): new source docs for the crash input and the
  heading-loss patterns make every projection (`report.yaml` / `docgraph.yaml` /
  `reassembled.md`) visible in one diff; `test_model_invariants` gains the
  toc-count-equals-heading-block-count and inline-span-containment assertions, so a
  regression fails even if goldens are regenerated without review.
- **Unit tests** inline per project convention for `heading_info_for` (in `block_info.py`),
  and under `tests/docs/` for link-form classification, reference-definition surfacing,
  `prose_text()` stripping, and `block_at_offset()`.
- `make lint` (zero ruff/basedpyright findings) and `make test` clean before each phase
  merges; goldens regenerated and reviewed for any intended projection change.

## Rollout Plan

Single **0.1.1** release covering both phases. As a preview-stage library with no
downstream-compatibility obligations, changes take the cleanest shape (e.g. `Link.form`
is required, not a defaulted add-on); there are no compatibility shims or aliases. Note:
`docs/publishing.md`'s letter would treat signature changes as a pre-1.0 **minor** (0.2.0)
bump — shipping as 0.1.1 is the maintainer's call given preview status and is trivial to
relabel if desired (see Open Questions). CHANGELOG records the fixes and additions; the
tag triggers the PyPI publish per `docs/publishing.md`.

## Open Questions

1. **`links()` and images.** Surface images in `links()` with `form=image` (symmetry with
   the other forms), or keep `links()` link-only and surface images only via the node
   table's `NodeKind.image`? Recommendation: node-table only — `links()` stays "links,"
   and `form` never returns `image` from `links()`.
2. **`prose_text()` replacement policy.** Default proposed: inline code dropped,
   links/images replaced by their text, inline-HTML/footnote-refs dropped. Confirm, or
   downgrade to a documented `collect()` recipe in `usage.md`.
3. **`collect()` inline ergonomics.** Behavior fix (inline-kind requests imply the
   full-node candidate set) vs. a docstring-only note. Recommendation: behavior fix — the
   silent `[]` is the documented footgun.
4. **Version label.** Shipping as 0.1.1 per decision; relabel to 0.2.0 if you prefer to
   follow `publishing.md`'s letter for signature changes. No code impact.

## References

- Issue [#6](https://github.com/jlevy/flexdoc/issues/6) — this plan's source.
- Issue [#5](https://github.com/jlevy/flexdoc/issues/5) — link forms / ref defs / `block_at_offset`.
- `docs/flexdoc-spec.md` §2 (Error posture: P17, builder vs input contracts), §4.3
  (node table / layer nesting), §7 (Sections and TOC — the heading-set rule), §8
  (Inline elements and links).
- `docs/project/specs/active/plan-2026-06-11-structural-metadata.md` — the `*_info`
  pattern this extends with `HeadingInfo`.
- `docs/publishing.md` — release/versioning.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
