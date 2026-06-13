# Feature: Document-Metrics Use Case — `node_table` crash, `sections()`/`toc()` heading loss, and inline/heading/link API completion

**Date:** 2026-06-13 (last updated 2026-06-13)

**Author:** Joshua Levy

**Status:** Implemented (2026-06-13). All beads
(`flexdoc-yhzm/w3uk/xjl8/0xky/jnvt/hwcl/1jrc`) landed; 322 tests pass, lint clean.
Targeted at **0.2.0** (breaking changes → pre-1.0 minor bump); the release is **not** cut
here — the version is labeled `0.2.0 (unreleased)` and the tag is held pending final
review. Release prep (`flexdoc-aa0l`) covers the CHANGELOG; tagging is the maintainer's action.

Two findings during implementation:

- The dogfood invariant test (Test-Suite Hardening (c)) immediately caught a *third* defect
  the section rewrite would have introduced: `AGENTS.md` embeds a `---`-fenced block that
  marko reads as a setext heading *inside* a blank-line paragraph, so a content paragraph
  straddled a later heading and the subtree-derived section spans overlapped (a
  document-layer nesting violation). Fixed by deriving each section's span from
  heading-block boundaries (heading start to the next same-or-higher heading, trimmed),
  which nests by construction and is byte-identical to the old span for well-formed docs.
  This is exactly the class of "real input breaks the model" the hardening targets.
- Linked images (`[![alt](img)](url)`) are excluded from the corpus: flowmark's atomic
  span for the outer link stops at the inner image's `)`, so neither its span nor its form
  classifies reliably. Out of scope here; the other forms all classify correctly.

## Overview

[pprose](https://github.com/jlevy/practical-prose) is retiring its hand-rolled
regex metrics (`metrics.py`) in favor of flexdoc's typed document model. Migrating
against flexdoc 0.1.0 surfaced two correctness bugs and a cluster of API gaps,
filed together as [#6](https://github.com/jlevy/flexdoc/issues/6) (link-form gaps
recapped from [#5](https://github.com/jlevy/flexdoc/issues/5)). This plan lands all
of them in one release, **0.2.0**.

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
  stays deferred for 0.2.0. The proper solution is mapped in **Appendix A** so #5 is fully
  accounted for.
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
cases = [
    "# A\nintro\n## B\nbody\n",              # tight: ## B glued below preceding text
    "# T\n\n<!-- marker -->\n## S\n\nx\n",   # ## S preceded by a non-blank line
]
for src in cases:
    d = FlexDoc.from_text(src)
    n = sum(1 for b in d.blocks() if b.type == BlockType.heading)
    print(n, len(d.toc()))   # both print "2 1": blocks() finds both; toc() drops one
```

(Verified against the current source: both cases give `blocks=2, toc=1`. A
well-formed `# A\n\nintro\n\n## B\n\nbody` and a blank-led `\n## Heading\n\nbody`
both give `2/2` and `1/1` respectively — the bug is specifically tight or
non-blank-preceded headings.)

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
shipped together as 0.2.0. Each fix is grounded in the existing design rather than a
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

4. **Link `form`, image access, and reference definitions** (`links.py`, `node.py`,
   `node_table.py`, `collect.py`). Add `LinkForm` (`StrEnum`: `inline`, `autolink`,
   `bare_url`, `reference`, `image`, `reference_definition`) and a required `Link.form`,
   classified in `block_links` from how each identity was located: `inline` (a
   `markdown_link` atomic containing `](`), `reference` (resolved by text against a
   definition), `autolink` (surrounded by `<>`), `bare_url` (a verbatim URL, no brackets),
   `image` (preceded by `!`; covers inline `![alt](url)` and reference `![alt][id]`, alt
   text in `Link.text`).
   `links()` returns **true links only by default** — `inline`, `reference`, `autolink`,
   `bare_url` — and takes `links(forms: set[LinkForm] | None = None)` to retrieve any form
   set; `images()` is a documented convenience for `links(forms={LinkForm.image})`. Image
   and image-link access is therefore first-class and easy, just not the `links()` default.
   Reference definitions come parser-authoritatively from marko's `Document.link_ref_defs`
   (`{id: (url, title)}`), spans recovered by locating the `[id]:` line; they are surfaced
   primarily as `NodeKind.link_ref_def` nodes (so `collect(kinds={NodeKind.link_ref_def})`
   counts them) and are retrievable via `links(forms={LinkForm.reference_definition})` —
   kept out of the default `links()` since a definition is not a link occurrence.

5. **Prose-text projection** (`flex_doc.prose_text()`). A method returning prose-only
   text for editorial linting: take prose-bearing blocks (`paragraph`, `heading`;
   exclude `code`, `table`, `html`, `thematic_break`, and frontmatter), use each block's
   **verbatim source slice** (not `reassemble()`, to preserve `" — "` spacing), and strip
   inline non-prose spans via the node table — inline `code_span` removed, `link`/`image`
   replaced by their text/alt, `footnote_ref` removed, and inline-HTML **tags** removed
   while the text they wrap is kept (`<span>foo</span> bar` becomes `foo bar`, since marko
   emits each tag as its own `inline_html` node and the wrapped text is ordinary text) —
   joining blocks with blank lines. Depends on Bug 1 being fixed (uses the node table).
   Ships as a real method, not a `collect()` recipe.

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
  `flexdoc.docs`). `links()` defaults to true links; new `links(forms=...)` filter and
  `images()` convenience; reference definitions are reached via `forms` or the node
  table, not the default `links()`.
- `NodeKind`: new `link_ref_def` member (a new kind in the cross-language `DocGraph`
  contract; any port must learn it).
- `FlexDoc`: new `prose_text()` and `block_at_offset()` methods.
- `collect()`: inline-kind requests no longer require `recursive=True`.
- `node_table`: inline nodes scoped per block; markdown heading `level` sourced from
  `HeadingInfo`; new `link_ref_def` nodes; link nodes carry `form`.

## Implementation Plan

### Phase 1: Correctness — crash and heading loss

- [x] `HeadingInfo` + `heading_info_for` in `block_info.py` (with inline tests); carry
      `heading_info` and `heading_level` on `Block`; populate in `block_tree._blocks_from`.
- [x] `node_table._build_markdown_nodes` reads `block.heading_info` for `attrs["level"]`;
      remove the `#`-counting/setext scan.
- [x] Scope `node_table._build_inline_nodes` inline discovery per leaf content block;
      parent links by full containment; keep `_validate_layer_nesting` intact.
- [x] Rewrite `flex_doc._section_list` to derive sections from top-level heading blocks;
      reuse/synthesize `Section.heading`; assign `content` by offset.
- [x] Regression tests: Bug 1 repro asserts no raise + correct inline nodes; Bug 2 repros
      assert `len(toc()) == #heading blocks` (tight and marker-preceded cases).
- [x] Golden corpus + invariants (Test-Suite Hardening (a)–(c)): add `inline_pathology.md`
      and `heading_edges.md`; add the cross-projection invariants (toc-count ==
      heading-block count, inline span ⊆ parent on the query surface, public inline
      `collect()`/`graph()` build without raising); add the dogfood test over the repo's
      own `.md`. Regenerate goldens (`UPDATE_GOLDEN=1`) and review the diff.

### Phase 2: Typed surface — links, prose text, ergonomics

- [x] `LinkForm` + `Link.form`; classify forms in `block_links`; surface
      `reference_definition` from `Document.link_ref_defs` with recovered spans.
- [x] `NodeKind.link_ref_def`; emit ref-def nodes and `form` on link nodes in
      `node_table`; export `LinkForm`; per-form tests including bare-URL vs autolink.
- [x] `FlexDoc.prose_text()` (node-table-backed strip); tests for inline-code/link
      stripping and `" — "` preservation.
- [x] `FlexDoc.block_at_offset()`; `collect()` inline-without-`recursive` fix; tests.
- [x] `link_taxonomy.md` corpus doc + link-form accounting invariant (Test-Suite
      Hardening (a)/(b)): every `links()` entry has a true-link form; `len(links()) +
      len(images()) + #ref-defs` equals the table's `link`/`image`/`link_ref_def` count.
- [x] `CHANGELOG.md` 0.2.0 section (Fixed: Bug 1, Bug 2; Added: heading level on `Block`,
      `LinkForm`/`Link.form` + reference-definition surfacing/`link_ref_def`,
      `prose_text()`, `block_at_offset()`, `collect()` inline ergonomics). Update
      `TODO.md` / spec references; tag `v0.2.0` per `docs/publishing.md`; close #6 (and
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

## Why These Bugs Escaped the Tests

These were not caught by a thin suite — the suite is substantial (golden artifacts
plus programmatic invariants over a 7-document corpus). They escaped for specific,
correctable reasons worth fixing at the root, because the *class* of each gap will
recur otherwise.

**The harness wiring was sound; the corpus and the invariant set were not.** Grounded
in the current source:

- **`node_table()` is already built for every corpus doc** (`test_model_invariants`),
  and `_validate_layer_nesting` raises on exactly the Bug-1 condition. So Bug 1 would
  have been caught the moment *any* corpus doc contained the pathological inline pattern
  (an empty fenced block adjacent to inline backticks, so backtick pairing crosses a
  block boundary). None of the seven docs do. This is a pure **corpus** gap.
- **`doc_report` already serializes sections/TOC, the full node table, and links**
  (debug.py), so a dropped heading *would* show in a golden `report.yaml` diff — but
  only if a doc triggered it. Every corpus heading is blank-separated and the first line
  of its paragraph (the one shape that works); none is tight or marker-preceded. So Bug 2
  is invisible in the golden diff **and** in the invariants, which never assert any
  cross-projection equality tying `sections()`/`toc()` back to `blocks()`.
- **The invariants check internal consistency only** — the base-block partition (P13),
  SpanRef round-trips, node-table reference integrity, DocGraph child validity, and
  `reassemble()` idempotence. None ties two projections together. An invariant of the
  form "`toc()` has one entry per top-level heading block" would have failed on the first
  heading-bearing doc once it included a tight/marker-preceded heading.
- **Link forms were never asserted.** `footnotes_refs.md` exercises autolinks, a
  reference link, and reference definitions, but no test checks that they *classify*,
  that a bare URL is distinguishable, or that a reference definition is counted — so the
  whole missing taxonomy went unnoticed.
- **`kitchen_sink.md` is broad, not adversarial.** It samples one clean instance of each
  construct, not the messy combinations real documents contain. The pprose migration
  found these precisely by running flexdoc over 61 real documents; the suite never
  dogfooded real Markdown — and this repo's own `AGENTS.md` (headings preceded by
  `<!-- ... -->` markers) reproduces Bug 2 on its own.

## Test-Suite Hardening

Root-cause fixes, landed *with* the bug fixes so each guards its own regression. (a)–(c)
are part of the bead work below; this section is the rationale and the checklist.

- **(a) Adversarial corpus docs** (each fixed bug's minimal repro becomes a permanent
  corpus doc, so the golden diff *and* the invariants both guard it):
  - `inline_pathology.md` — empty fence immediately followed by a line mixing indented
    and inline backticks; unequal-length backtick runs; adjacent code spans; inline code
    containing `]`/`)`; and a plain inline image. (Bug-1 class.)
  - `heading_edges.md` — a heading preceded by an HTML-comment marker with no blank line
    (the `AGENTS.md` pattern); a setext h1; a level jump (to h4); a heading inside a
    blockquote and inside a list item (must *not* become a document section); a fully glued
    (tight) heading/body pair; and a duplicate top-level title. (Bug-2 / section-content
    class.)
  - `link_taxonomy.md` — inline, reference (definition elsewhere), collapsed `[x][]` and
    shortcut `[x]` references, autolink `<url>`, bare URL, inline image, reference image,
    and used *and* unused reference definitions. (Exercises every `LinkForm`; linked images
    `[![alt](i)](u)` are a deliberate non-goal — see the note at the top of this plan.)
- **(b) Cross-projection invariants** added to `test_model_invariants` (corpus-wide, so
  every present and future doc is held to them):
  - `len(toc()) == count of top-level `heading` blocks`; each `Section.title` equals its
    heading block's `HeadingInfo.title`.
  - every located markdown inline node's span ⊆ its parent block's span — the nesting
    guarantee asserted on the *query surface* across the whole corpus, not only at build.
  - `node_table()`, `graph()`, and `collect(kinds=…, recursive=True)` for each inline
    kind (`link`, `image`, `code_span`, `footnote_ref`, `link_ref_def`) build without
    raising — exercising the *public* inline path Bug 1 broke, not just the internal build.
  - link-form accounting: every `links()` entry has a true-link form, and
    `len(links()) + len(images()) + #ref-defs` equals the count of `link` / `image` /
    `link_ref_def` nodes in the table.
- **(c) Dogfood real Markdown** (highest value, lowest cost): a test that parses every
  `.md` under the repo (`docs/`, the specs, `AGENTS.md`, `README.md`, …) and asserts only
  the invariants (no goldens). This mechanically reproduces the pprose discovery loop and
  catches "crashes or loses data on real input" for free as the repo's own docs evolve;
  `AGENTS.md` alone would have caught Bug 2.
- **(d) Process**: adding the minimal repro to the corpus is the required closing step of
  any document-model bug fix — the standing rule that turns each escape into a permanent
  guard.

## Rollout Plan

Single **0.2.0** release covering both phases. The release carries breaking signature
changes (e.g. `Link.form` is required, not a defaulted add-on; `links()` / `collect()`
defaults adjusted), so per `docs/publishing.md`'s pre-1.0 rule — breaking changes bump the
**minor** version — this is a 0.2.0 minor bump, not a patch. As a preview-stage library with
no downstream-compatibility obligations there are no compatibility shims or aliases.
CHANGELOG records the fixes and additions; the release is **not** being cut here — the
version is labeled `0.2.0 (unreleased)` and the `v0.2.0` tag (which triggers the PyPI publish
per `docs/publishing.md`) is held pending final review.

## Resolved Decisions

Settled in review (2026-06-13):

- **Images stay out of the `links()` default.** `links()` returns true links only;
  `images()` and `links(forms={...})` provide first-class, documented access to images
  and any other form. Reference definitions likewise come via the node table or
  `links(forms=...)`, never the default — a definition is not a link occurrence.
- **`prose_text()` drops inline-HTML tags but keeps the text they wrap**
  (`<span>foo</span> bar` -> `foo bar`); inline code is dropped and links/images become
  their text/alt. It ships as a real method, not a `collect()` recipe.
- **Behavior fixes, not doc-only notes**, in every case — including the `collect()`
  inline-without-`recursive` footgun.

## Open Questions

None outstanding. Version is **0.2.0** — the breaking signature changes are a pre-1.0 minor
bump per `docs/publishing.md`; the release is not yet cut (held for final review, see
Rollout).

## References

- Issue [#6](https://github.com/jlevy/flexdoc/issues/6) — this plan's source.
- Issue [#5](https://github.com/jlevy/flexdoc/issues/5) — link forms / ref defs / `block_at_offset`.
- `docs/flexdoc-spec.md` §2 (Error posture: P17, builder vs input contracts), §4.3
  (node table / layer nesting), §7 (Sections and TOC — the heading-set rule), §8
  (Inline elements and links).
- `docs/project/specs/active/plan-2026-06-11-structural-metadata.md` — the `*_info`
  pattern this extends with `HeadingInfo`.
- `docs/publishing.md` — release/versioning.

## Appendix A: Deferred — Fuzzy `SpanRef` Re-anchoring (#5 item 4)

Mapped here so #5 is fully accounted for; **not implemented in 0.2.0** (spec §11 and §14
keep it deferred). #5 item 4 wants a `SpanRef` to re-anchor after the two-phase linter edits
the text around — or inside — a referenced span. Today `resolve()` (`span_ref.py`) is an
exact ladder: offset fast path, then exact full-text search, then prefix/suffix
disambiguation among the exact occurrences; if `exact` itself was edited it returns `None` by
design (a wrong location is never guessed). Fuzzy re-anchoring adds approximate recovery as
an explicit, scored, opt-in fallback.

### Approach: extend the ladder, leave the exact contract intact

Run the existing exact ladder first and unchanged (it stays pure and total), then add fuzzy
rungs that fire only when the exact ladder misses and the caller opts in — the battle-tested
Hypothesis / Apache Annotator order
(`docs/project/research/research-2026-05-30-span-references.md` §3):

1. offset fast path (exact text at `start`/`end`) — implemented.
2. exact quote search, prefix/suffix-disambiguated — implemented.
3. **offset-hinted fuzzy search**: best approximate match of `exact` within a bounded window
   around the `start` hint (match on `prefix+exact+suffix` when `exact` is short and the
   context disambiguates).
4. **full-document fuzzy search**: if there is no hint or the window misses, the best
   above-threshold match across the whole source.

### API shape (recommended)

Keep `resolve()` exact-only and add a separate, explicit entry point, so an approximate hit
is never silently taken for an exact one:

```python
@dataclass
class FuzzyMatch:
    span: tuple[int, int]
    score: float  # 0..1 similarity; 1.0 == exact
    exact: bool

def resolve_fuzzy(
    span_ref: SpanRef,
    source_text: str,
    *,
    min_score: float = 0.7,
    hint_radius: int | None = None,
) -> FuzzyMatch | None: ...
```

`resolve_fuzzy()` delegates to `resolve()` first (returning `score=1.0, exact=True` on a
hit), then tries rungs 3–4 and returns the best match at or above `min_score`, else `None`.
This keeps the spec's "failure is a value" posture and the "quote canonical, offset a hint"
principle: a caller must opt in to a guess and receives a confidence it can gate on (e.g.
require a high score before re-applying a correction). `resolve()` and `resolve_and_update()`
are untouched; the addition is purely additive to `span_ref.py`.

### Matching primitive and the dependency gate

The standard primitive is Google **diff-match-patch** `match_main` (Bitap) with a hint offset
and threshold (research §3). Two paths:

- **diff-match-patch (higher fidelity).** Bitap caps the pattern near 32 characters, so for a
  longer `exact` match on a ≤32-char anchor slice (the head of `exact`, or the prefix/suffix
  window) and verify/extend the full quote around the located point. It adds a third-party
  dependency, which under this repo's policy needs the 14-day cool-off plus a recorded
  exception (`SUPPLY-CHAIN-SECURITY.md`, `pyproject.toml` `exclude-newer`). That gate is the
  main reason to hold it out of 0.2.0.
- **No-dependency fallback.** A bounded `difflib.SequenceMatcher.ratio()` (stdlib; consistent
  with the existing `cydifflib` use) scored over candidate windows around the hint and across
  the document. Lower recall than Bitap but ships with no new dependency and no cool-off.

Recommendation: prototype with the stdlib fallback to settle the API and thresholds at zero
supply-chain cost, and adopt diff-match-patch only if the fallback's recall proves
insufficient.

### Decisions to settle at implementation time

- `min_score` default and the edit-distance-to-similarity normalization, tuned so genuinely
  deleted text returns `None` rather than a wrong location.
- Tie-breaking among near-equal candidates: nearest the offset hint first, then best
  prefix/suffix agreement (reuse `_best_match`'s scoring over the fuzzy candidates).
- Whether `resolve_and_update()` ever writes back a fuzzy span — recommend no: keep the
  exact-only hint contract; a fuzzy result is returned, not persisted as an exact hint.
- Offsets stay Unicode code points (P1); the primitive must operate on the code-point string.

### Testing

A corpus of `(original SpanRef, edited source)` pairs — edits inside `exact`, inside
`prefix`/`suffix`, span relocation, and genuine deletion — asserting the recovered span for
the recoverable cases, a descending `score`, and `None` (not a wrong guess) when the quote is
truly gone.

### Tracking

A new deferred bead (`tbd`), blocked on the supply-chain decision above; spec §11 and §14
remain the source of record.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
