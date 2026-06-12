# Feature: FlexDoc Package Extraction (Staged)

**Date:** 2026-06-11 (last updated 2026-06-12)

**Author:** Joshua Levy

**Status:** Stage 1 shipped (chopdiff, PR #26 merged). Stage 2 Steps 1–3 (extract +
scaffold + verify) and Stage 2.5 (pre-publish design refinement, from the 2026-06-12
review) are done in this repo, tracked as beads `flexdoc-7yfb/gvzk/3xhq/hqi1/32s0/
6a5i/6off/tfg8/mbdt` (all closed). Steps 4–5 (publish + rewire chopdiff) are pending.
Stages 3–5 are forward-looking.

> **Repo note.** This is flexdoc's copy of the extraction plan. It was authored in
> chopdiff (where Stage 1 happened) and now lives in the extracted package, which is the
> Stage 2 destination. Where the original runbook said "the new repo," that repo is
> *this* one. Cross-references to chopdiff's plan specs and `docs/textdoc-spec.md` were
> copied alongside it under `docs/project/` so the design history travels with the model.

## Overview

The document/markdown model that chopdiff grew — `TextDoc`, the block/section/inline
structure, the node table and `DocGraph`, span references, html-in-md, frontmatter — is a
general, reusable *document layer* that does not depend on chopdiff's diff and
windowed-transform machinery. This plan extracts it into a standalone package (**flexdoc**)
so it can be used and evolved on its own, and so chopdiff becomes a thin diff/transform
layer built **on** flexdoc.

flexdoc's north star reaches past the extraction: to be one of the most flexible
foundations in Python for processing and understanding complex documents — for careful
editing and for deep analysis alike. The aim is to identify and understand a complex
Markdown document at a genuinely granular level along several independent axes at once:
its **Markdown syntax** (blocks, inline elements, exact spans, typed attributes), its
**grammar and language** (paragraphs, sentences, tokens, lemmas, and further linguistic
structure), and, where useful, **other structures** layered onto the same text (marked-up
regions, citations, annotations). That granularity is what enables the use cases driving
this work: deep textual analysis, source-grounded annotation and cleanup of documents, and
structural editing that survives reparse. The package extraction is the enabling first
step; the forward design (Stage 3) is where flexdoc grows into that role, on the layered
model the unified-document-model plan has already settled (see North star below).

The work is split into stages, each on its own branch (and, from Stage 2, its own repo):

1. **Stage 1 — in-repo refactor (done, in chopdiff).** A pure, behavior-preserving split
   into two import roots (`src/flexdoc/` and `src/chopdiff/`) shipped in a single wheel,
   proving and *enforcing* a one-way dependency cut (`flexdoc` imports nothing from
   `chopdiff`).
2. **Stage 2 — extract and publish (this repo).** Lift `src/flexdoc/` and its tests into a
   standalone package, give it its own packaging and dependency subset, publish to PyPI,
   then rewire chopdiff to depend on it (the single intended breaking release).
   **Stage 2.5** sits between extraction and publish: the pre-publish design refinement
   driven by the standalone review, taken now because breaking changes are free before
   0.1.0 (chopdiff adapts once, at rewire).
3. **Stage 3 — flexdoc as a first-class, extensible document-layer API** (later).
4. **Stage 4 — fold in the synthetic layer** (optional, later).
5. **Stage 5 — standalone cleanup and polish** (the immediate post-extraction tidy; see
   the final phase).

## Goals

- **A self-contained document-layer API.** `flexdoc` is the markdown/document model
  (parse → `TextDoc`/`DocGraph`, `collect()`, spans/`SpanRef`, sections, frontmatter,
  render, html-in-md), usable with no dependency on chopdiff.
- **Granular, multi-axis understanding.** Expose a document's structure at a fine grain
  across independent axes — Markdown syntax, linguistic structure, and other layered
  structures — over one shared, source-grounded coordinate space.
- **Flexible and extensible by construction.** New parse layers, node kinds, typed
  attributes, and analyzers are additive; they extend the model without reshaping its core.
- **A correct, enforced one-way boundary (Stage 1).** `flexdoc` never imports `chopdiff`;
  `chopdiff` imports `flexdoc`. Enforced in Stage 1 by a dependency-free test; in Stage 2
  the boundary becomes structural (flexdoc has no chopdiff dependency at all).
- **A mechanical, low-risk split and release (Stage 2).** With the boundary proven, giving
  `flexdoc` its own `pyproject.toml`, repo, dependency subset, and PyPI release is a
  lift-and-shift; chopdiff's switch to the external `flexdoc` is the single intended
  breaking release.

## Non-Goals

- **No behavior or API changes in Stages 1–2.** Module locations and import paths move; the
  public behavior of the document model does not.
- **No synthetic-layer / `divs` fold-in now.** Re-expressing `divs`/`TextNode` as flexdoc's
  synthetic layer is Stage 4.
- **No backward-compatibility shims.** Old `chopdiff.docs.*` paths are not aliased; the
  break lands intentionally in chopdiff's Stage 2 release.
- **No heavy analysis dependencies in the core.** Linguistic/NLP, layout, and
  domain-specific analysis attach through optional, pluggable analyzers and extras;
  flexdoc's base model keeps its current light dependency set (and the supply-chain cool-off).

## Background

### The dependency graph decides the cut

Mapping the internal imports across chopdiff's five top-level modules made the boundary
almost entirely forced, not a matter of taste:

- `docs/` ↔ `html/` are **mutually dependent** (`docs/sizes.py` imports
  `html.html_plaintext`; `html/timestamps.py` imports `docs.search_tokens`/`docs.wordtoks`),
  so they stay on the same side.
- `util/` imports nothing internal (a leaf) and `docs/` depends on it, so `util/` follows
  `docs/`.
- `{docs, html, util}` is **closed**: nothing in it imports `divs` or `transforms`. This is
  the flexdoc cluster.
- `transforms/` depends only on `docs` + `util` (both flexdoc) and nothing imports it — the
  chopdiff side.
- `divs/` is a **pure consumer** (imports `docs` + `html`; nothing depends on it), so it can
  sit on either side. Resolved: stays in chopdiff (see Resolved Decisions).

A consequence of moving whole modules to preserve code: `docs/token_diffs.py` — the diff
*primitives* — travels into flexdoc with the rest of `docs/`, because it is cyclically tied
to `docs.text_doc`. So flexdoc carries the token-diff *algorithm*; chopdiff keeps the diff
*filters* and windowed transforms. Relocating `token_diffs` later is a separate finer
refactor (Stage 3 candidate).

### The module cut

| Module | Destination | Reason |
| --- | --- | --- |
| `docs/` | **flexdoc** | The document model core; mutually dependent with `html/`. |
| `html/` | **flexdoc** | html-in-md/plaintext/tags/extractor/timestamps; cycle with `docs/`. |
| `util/` | **flexdoc** | Leaf utilities `docs/` depends on (read-time, token estimation). |
| `transforms/` | **chopdiff** | Diff filters + windowed transforms; depend on flexdoc. |
| `divs/` | **chopdiff** | Pure consumer; becomes flexdoc's synthetic layer at Stage 4. |

`lemmatize` was moved out of flexdoc into `chopdiff.util` in Stage 1 (PR #26) — it is used
only by the diff filters, not the document model — so `simplemma` is chopdiff's optional
extra, not flexdoc's, keeping the flexdoc core dependency-light.

### Dependency partition (verified)

flexdoc's runtime dependencies, partitioned from chopdiff and **verified against the merged
Stage-1 tree** in this repo:

```
prettyfmt  flowmark  marko  strif  funlog  cydifflib  regex
selectolax  pydantic  frontmatter-format  typing-extensions
```

Verification notes (these tripped up the naive form of the check; re-verify the same way):

- **`selectolax` is imported function-locally** in `src/flexdoc/html/html_tags.py`
  (`from selectolax.parser import HTMLParser` inside functions). A scan anchored to
  column-0 `^(from|import)` misses it. Use a scan that also catches indented imports
  before concluding a package is unused.
- **`typing-extensions` is a direct import** (`from typing_extensions import override`,
  five modules) for Python 3.11 support, so it is declared explicitly rather than relied on
  transitively via pydantic.
- **`simplemma` is intentionally absent** (lemmatize is now `chopdiff.util`).
- No optional extras.

## Stage 1 — pure in-repo refactor (done, in chopdiff)

One wheel, two import roots, behavior preserved, boundary enforced. Shipped on chopdiff's
`main` (PR #26). It moved `docs/`/`html/`/`util/` under `src/flexdoc/`, rewrote
`chopdiff.{docs,html,util}` imports to `flexdoc.*` across the tree, added
`tests/test_package_boundary.py` (asserts via `ast`, stdlib only, that no `src/flexdoc`
module imports `chopdiff`), set the wheel target to both roots, and kept `make lint`/`make
test` green.

## Stage 2 — extract flexdoc to its own repo and publish (this repo)

With the boundary proven, this is copy-and-rewire plus packaging. The partition was computed
from the merged Stage-1 tree; **re-verify each fact against the source before relying on it**
(this refinement records the facts as re-verified on 2026-06-12).

### Step 1 — copy the package, tests, examples, and design history (done)

- [x] Copy `src/flexdoc/` verbatim (the whole package: `docs/`, `html/`, `util/`,
      `__init__.py`, `py.typed`). Inline tests (`## Tests` sections) travel with their
      modules.
- [x] Copy the document-model **tests**: `tests/docs/`, `tests/html/`, `tests/golden/`
      (with `documents/`, `expected/`, `README.md`), and `tests/__init__.py`. **Do not**
      copy `tests/test_package_boundary.py` (the boundary becomes a real package
      dependency). `tests/divs/`, `tests/transforms/`, and `tests/util/` stay in chopdiff.
- [x] **Correction to the original runbook:** `tests/html/test_html_validation_and_classes.py`
      was a *mixed* file — one flexdoc test (`tag_with_attrs`) plus one chopdiff test
      (`parse_divs`, importing `chopdiff.divs`). Copying `tests/html/` wholesale therefore
      pulled a cross-boundary import that fails to collect in the standalone package. The
      flexdoc test was kept and the divs test dropped (chopdiff retains its copy). **General
      rule:** after copying tests, grep the copied tree for any `chopdiff` import and prune
      or relocate it — do not assume a test directory is purely on one side of the cut.
- [x] `tests/test_supply_chain.py` is **repo-agnostic** (it reads `pyproject.toml`/`uv.lock`/
      the marker doc), so it is copied as-is rather than rewritten — a simplification over
      the original runbook's "write a fresh one."
- [x] Copy the flexdoc-only **examples** (`normalized_form.py`, `doc_structure.py`,
      `backfill_timestamps.py`; verified to import only `flexdoc.*`). `insert_para_breaks.py`
      uses `chopdiff.transforms`, so it stays in chopdiff. **Correction:** each example's
      PEP 723 `# dependencies` block listed `chopdiff`, not `flexdoc` (it worked only
      because flexdoc shipped inside the chopdiff wheel). Rewritten to `flexdoc`; two
      docstrings that described "chopdiff's" features were reframed to flexdoc.
- [x] Copy the **design history**: `docs/textdoc-spec.md` (design of record), the research
      briefs under `docs/project/research/`, and the plan specs
      `plan-2026-05-29-unified-document-model.md`, `plan-2026-06-11-structural-metadata.md`,
      `plan-2026-05-31-doc-model-refinements.md`, `plan-2026-05-31-golden-doc-testing.md`,
      and this extraction plan.

### Step 2 — scaffold the new repo's tooling (done)

This repo was bootstrapped from the same `simple-modern-uv` template as chopdiff, so the
Makefile, `devtools/lint.py`, ruff/basedpyright/pytest config, and workflows already
matched closely; the deltas below are what made it flexdoc-specific and chopdiff-equivalent.

- [x] `pyproject.toml`: `name = "flexdoc"`, `requires-python = ">=3.11,<4.0"`; hatchling +
      uv-dynamic-versioning; `[tool.hatch.build.targets.wheel] packages = ["src/flexdoc"]`;
      the 11 runtime dependencies above (no extras); the `audit` group (`pip-audit`); and
      the ruff/basedpyright/codespell/pytest config matching chopdiff. Removed the scaffold's
      `[project.scripts]` entry point (flexdoc is a library, not a CLI).
- [x] **Supply-chain cool-off mirrors chopdiff exactly** (so the shared dependencies resolve
      to the same vetted versions and the two repos advance one policy together): global
      `exclude-newer = "2026-05-11T00:00:00Z"`, with per-package exceptions for
      `strif` (2026-05-24), `flowmark` (2026-05-30), and `idna` (2026-05-13).
      `SUPPLY-CHAIN-SECURITY.md` documents all three plus the one audit-gate ignore. A
      `tests/test_supply_chain.py` guard checks the lock cutoff matches config and that every
      exception is documented.
- [x] **uv resolution-stability gotcha (worth recording):** a per-package `exclude-newer`
      exception does **not** move an already-locked version on its own — uv keeps the locked
      version if it still satisfies constraints. The first `uv lock` (under the global
      2026-05-11 cutoff) pinned `idna 3.14`; widening only idna's exception left it at 3.14.
      Forcing the CVE fix required `uv lock --upgrade-package idna`, which pulled `idna 3.15`
      (matching chopdiff). With idna fixed, the audit gate ignores only `PYSEC-2026-196` in
      `pip` (a pip-audit tool transitive dep, never shipped), identical to chopdiff.
- [x] `devtools/lint.py`: added `examples` to `SRC_PATHS` (matching chopdiff) so examples are
      linted and type-checked.
- [x] CI (`ci.yml`): `build` (3.11–3.14, `uv sync --locked`, lint `--check`, pytest),
      `audit` (`pip-audit --ignore-vuln PYSEC-2026-196`), and `wheel-smoke` — the smoke job
      imports **only** `flexdoc` from an isolated wheel install (chopdiff's smoke imported
      both roots). `publish.yml` mirrors chopdiff's `--locked` (fixed-cutoff) form.
- [x] Fresh `README.md` and `CHANGELOG.md`; `SUPPLY-CHAIN-SECURITY.md`; `AGENTS.md` carries
      chopdiff's engineering guidelines (minus the tbd block, as flexdoc is not a tbd repo);
      `LICENSE` and `.gitignore` from the scaffold. `src/flexdoc/__init__.py`'s docstring was
      corrected (it listed `flexdoc.util` as "lemmatization and token estimation"; lemmatize
      left in Stage 1, so it is now "read-time and token-count estimation") and reframed to
      describe flexdoc as a standalone library.
- [x] `uv lock` (committed) and `make install`.

### Step 3 — verify flexdoc standalone (done)

- [x] `make lint` clean (66 source files, 0 errors) and `make test` green (305 passed —
      the document-model suite, the goldens, and the supply-chain guard).
- [x] `uv build` produces `flexdoc-*.whl` + sdist; isolated-venv smoke test installs the
      wheel and runs `import flexdoc; from flexdoc.docs import TextDoc;
      from flexdoc.html import html_to_plaintext; TextDoc.from_text(...)`. The boundary is now
      structural: flexdoc has no chopdiff dependency at all.

### Stage 2.5 — pre-publish design refinement (between Steps 3 and 4)

Driven by the standalone review
([`senior-engineering-review-flexdoc-standalone-2026-06.md`](../../review/senior-engineering-review-flexdoc-standalone-2026-06.md)),
which re-verified the v0.3.1 review's findings as fixed and identified the remaining
first-release hygiene. Taken **before** 0.1.0 because this is the one window where
breaking changes are free: nothing is published, and chopdiff adapts once at rewire
(Step 5). The constraint is the client compatibility bar from the maintainer: the
refined library must be at least as capable as what chopdiff ships today; renames and
removals are fine, capability regressions are not. Every item keeps `make lint`/`make
test` green and the golden fixtures unchanged (these are Python-surface changes, not
parse-behavior changes).

Breaking cleanups (done first, they shape the 0.1.0 surface):

- [x] **Drop the deprecated `collect()` aliases** (review F1): `scope` (also positional)
      and `contains` removed from `flexdoc.docs.collect.collect` and the
      `TextDoc.collect` bridge; both fully keyword-only. Alias tests rewritten to
      `subtree_of`/`within`; the alias-error cases removed.
- [x] **Close the editing-view naming seam** (review F3): `TextDoc.block_at_offset` →
      `paragraph_at_offset`, `iter_blocks` → `iter_paragraphs`,
      `Section.own_blocks`/`subtree_blocks` → `own_paragraphs`/`subtree_paragraphs`;
      `filtered()` docstring rephrased in paragraph terms; spec/example references
      updated. "Block" now always means the structural layer, "paragraph" the blank-line
      editing view, matching spec §6. chopdiff's own code was verified to use none of
      the renamed/removed surfaces, so the Step 5 rewire is unaffected.
- [x] **Settle the export surface in one pass** (review F2): `flexdoc.docs` now exports
      the typed block metadata (`CodeInfo`/`TableInfo`/`ListInfo`), the `SpanRef`
      resolvers (`resolve`/`resolve_and_update`), `parse_blocks`/`walk_blocks`/
      `block_type_for`, and the renamed `DEFAULT_INCLUDE`; `flexdoc.html` exports the
      missing `html_in_md` siblings (`html_p`, `html_tag`, `escape_attribute`,
      `tag_wrapper`, `identity_wrapper`). `IntervalIndex` and `node_table`/`render`
      internals stay private. README needed no changes (its imports were already
      package-surface). Discovered during the split: `_block_links` is a cross-module
      primitive, so it was promoted to public `block_links` in `flexdoc.docs.links`
      rather than crossing module boundaries underscore-named.

Non-breaking refinements (done):

- [x] **Split `text_doc.py`** (review F4): 1312 → 788 lines. Editing units moved to
      `paragraphs.py` (`Paragraph`, `Sentence`, `Offsets`, `SentIndex`, splitter hook),
      link extraction to `links.py` (`Link`, `block_links`), `Section` to `sections.py`;
      `text_doc.py` keeps `TextDoc` and the caching infrastructure. The `flexdoc.docs`
      package surface is unchanged; `flexdoc.docs.text_doc` still resolves `TextDoc`
      (canonical) and the names it itself uses.
- [x] **Memoize `sections()`** (review F5) via `_memoized_derivation`
      (`_cached_sections`), returning a fresh shallow copy per call like `blocks()`.
- [x] **Tighten the cross-language contract** (review F6): `AttrValue` JSON-safe alias
      on `Node.attrs`; `NodeModel.attrs` validated as `pydantic.JsonValue` at `DocGraph`
      emission (committed JSON Schema regenerated); a determinism test pins contiguous
      preorder node-id assignment across rebuilds.
- [x] **Enforce `LAYER_NESTING` in `build_node_table`** (review F7): tree layers check
      child-span-within-parent, ordered layers check sibling order/non-overlap; the
      whole golden corpus passes with validation on.

Docs and polish (review P3 sweep, done):

- [x] Spec reframed to flexdoc voice (§3, §6, §8), the stale deprecated-alias note in §9
      removed, the §13 "FlexDoc" naming disambiguation added, and the §15 source-module
      list updated for the split; one-line origin notes added to the four copied plan
      specs and three research briefs.
- [x] `read_time` documented as a downstream convenience (no internal users); the
      Pydantic-at-the-boundary / dataclasses-in-the-core rationale recorded in
      `doc_graph.py`'s module docstring.
- [x] Targeted inline tests added for `escape_attribute` and `html_p`/`html_tag`
      (pinning the p/div default-padding behavior); `render` helpers already had inline
      tests; `visualize_wordtoks` left untested (debug printer, a trivial test adds no
      coverage).
- [x] Explicit non-actions, per the review: no wordtok sentinel redesign, no root-level
      re-exports, no Pydantic/dataclass unification, no `DocumentSnapshot`, no offset
      micro-optimization without a benchmark; the `frontmatter.py` swap to
      `fmf_split_frontmatter_string` stays blocked on the upstream `frontmatter-format`
      release + cool-off exception (maintainer sign-off).

Verified after the stage: `make lint` clean, 305 tests green (goldens unchanged),
examples run, `uv build` + isolated-venv wheel smoke test exercising the new API
(`paragraph_at_offset`, settled exports) passes.

### Step 4 — publish flexdoc (pending; maintainer-gated; after Stage 2.5)

- [ ] Land Stage 2.5 first, so 0.1.0's first published API is the refined one (no
      deprecated aliases, settled exports, closed naming seam) and chopdiff's rewire
      targets the final names in one pass.
- [ ] Confirm the distribution name `flexdoc` is available on PyPI — verified available
      2026-06-12 (pypi.org returns 404 for `flexdoc`); re-check at publish time. Resolve
      the textdoc-spec §13 name collision (Stage 2.5 / Open Questions). Configure the
      PyPI Trusted Publisher for `jlevy/flexdoc` (`docs/publishing.md`).
- [ ] Tag and publish `flexdoc 0.1.0` (its own version line) via `publish.yml`. Publishing
      is irreversible; it is the maintainer's call to trigger.

### Step 5 — rewire chopdiff to the external flexdoc (pending; the breaking release)

- [ ] In chopdiff: `git rm -r src/flexdoc/` and the moved tests
      (`tests/{docs,html,golden}/`, `tests/test_package_boundary.py`); keep
      `tests/{divs,transforms,util}/`. The `chopdiff.{transforms,divs,util}` code already
      imports `flexdoc.*`, so **no import rewrite is needed** — those imports now resolve to
      the external package. (Note: the `tests/html/...validation_and_classes` divs test that
      flexdoc dropped stays valid in chopdiff, which still has `chopdiff.divs`.)
- [ ] `pyproject.toml`: add `flexdoc>=<first published>`; **remove** the now-flexdoc-only
      deps (`marko`, `cydifflib`, `funlog`, `regex`, `strif`, `frontmatter-format`,
      `pydantic`, `selectolax`, and the `typing-extensions` that flexdoc now owns directly);
      **keep** `flowmark` and `prettyfmt` (used directly by `transforms`/`divs`) and the
      `simplemma` extra (used by `chopdiff.util.lemmatize`). Set the wheel target back to
      `["src/chopdiff"]`. `uv lock`.
- [ ] `make lint`/`make test` green against the published flexdoc; the chopdiff `wheel-smoke`
      now imports only `chopdiff` (with `flexdoc` pulled as a dependency).
- [ ] `CHANGELOG.md`: chopdiff's first release depending on external flexdoc — a **breaking**
      release (the `chopdiff.docs|html|util.*` paths are gone). Note the migration
      (`pip install flexdoc`; `chopdiff.docs.* -> flexdoc.docs.*`). Merging/releasing is the
      maintainer's call.

## North star: a layered, extensible document model

What makes flexdoc flexible is a shape: a **stable node table over a single source-grounded
coordinate space**, with the document's many structures expressed as **independent,
composable parse layers** rather than one privileged tree. This is the architecture the
design of record (`docs/textdoc-spec.md`, principles P1–P5) and the unified-document-model
plan settled, much of which already ships. The granularity the vision asks for falls out of
three properties:

- **One coordinate space, many layers.** Every layer anchors to the same
  Unicode-code-point offsets; a node is `{id, kind, layer, parent, children, source_span,
  attrs}`. Layers coexist by span, so overlapping/cross-cutting structures are all
  representable without forcing one hierarchy.
- **One query, any grain.** A single `collect()` primitive — by `kinds`/`where`, by
  within-layer subtree, or by cross-layer offset-containment (`within`/`overlaps`),
  restricted by `layer` — answers everything; values, counts, and relationships are ordinary
  Python over the result.
- **One reference type.** `SpanRef` (quote-canonical, offset-hinted) anchors annotations and
  edits to the text so they survive reparse.

The three axes map onto layers, each an **extension axis, not a fixed schema**: Markdown
syntax (`markdown` layer, most complete), grammar/language (`textual` + optional analyzers),
and other structures (`synthetic`/`annotation`/`layout`). Two principles keep this flexible
without becoming heavy: **keep the core light, make enrichment pluggable** (heavier analysis
attaches through an analyzer interface as optional extras), and **extend by adding layers and
kinds, never by reshaping the core**.

## Stage 3 — flexdoc as a first-class, extensible document-layer API (later)

This is where flexdoc takes up its role; thorough and careful, detailed in flexdoc's own
forthcoming specs rather than frozen here.

- [ ] Settle and document flexdoc's public surface (including the deferred root-level
      re-exports) as one coherent document-layer API.
- [ ] Make the driving use cases first-class and tested — deep textual analysis,
      source-grounded annotation/cleanup, reparse-stable editing — with worked examples.
- [ ] Land the remaining unified-document-model phases (annotation, cross-layer edits,
      layout) in flexdoc; the model core already ships (textdoc-spec §14).
- [ ] Add the optional **analyzer interface** for the grammar/language axis (opt-in backends,
      light core preserved); deepen the Markdown and other-structure axes as needed.
- [ ] Document the extension contract (add a `Layer`/`NodeKind`/`attrs`/analyzer); revisit
      `token_diffs` placement.

## Stage 4 — fold in the synthetic layer (optional, later)

- [ ] Re-express `divs`/`TextNode`/`parse_divs` as flexdoc's synthetic layer
      (unified-document-model Phase 3), keyed into the node table by span. If `divs` is
      migrated out of chopdiff, this is where it lands.

## Stage 5 — standalone cleanup and polish (final phase)

The immediate post-extraction tidy: small, behavior-preserving improvements that make
flexdoc clean *as its own package*, separate from Stage 3's larger forward design. None of
these change the public model's behavior; they remove chopdiff-era residue and tighten the
standalone surface. Most can land before or alongside Stage 3.

- [x] **Purge stale `chopdiff` references in flexdoc prose** (catalogued during the
      extraction; all were cosmetic, none functional): the `text_doc.py` markup-check
      comment, the `block_tree.py` block-boundary docstring, the `test_block_types.py`
      offset comment, and the `doc_structure.py` sample prose now say flexdoc. The one
      remaining mention — `flexdoc/__init__.py` noting that chopdiff builds on flexdoc — is
      deliberate, describing the package relationship.
- [x] **Decide flexdoc's top-level public surface (resolved for Stage 2: keep
      submodule-only).** `flexdoc/__init__.py` exposes no root API by design and its
      docstring defers convenience re-exports "so the top-level API is designed once rather
      than piecemeal" — adding curated re-exports (e.g. `TextDoc`, `collect`, `SpanRef`)
      piecemeal at extraction time would contradict that recorded intent. Root re-exports
      are therefore part of Stage 3's "settle the public surface," where the whole API is
      designed together. Revisit there.
- [x] **Resolve the FlexDoc naming collision / trim the design-history docs** — moved into
      Stage 2.5's docs-and-polish sweep, since both must land before 0.1.0 publishes.
- [ ] **Audit docstrings/`README` examples** for correctness against the standalone API
      (the import-path portion lands with Stage 2.5's export pass) and add a couple of
      runnable examples specific to flexdoc's use cases.
- [ ] **Revisit `token_diffs` placement** (kept in flexdoc by the `docs` cycle) and whether
      the `tests/html/...validation_and_classes` file should be renamed now that its
      div-class test is gone.

## Testing Strategy

- **Stage 1 acceptance:** the existing inline + `tests/` suite passes unchanged after the
  moves and import rewrites, plus the boundary test and a one-wheel/two-root build smoke
  check.
- **Stage 2:** flexdoc's suite passes standalone (305 tests here), `make lint` clean, the
  wheel imports from an isolated install; after Step 5, chopdiff's suite passes against the
  published flexdoc; both repos green in CI.
- **Stages 3–5:** per the unified-document-model plan and flexdoc's own forthcoming specs;
  Stage 5 cleanups must keep `make lint`/`make test` green and the goldens unchanged.

## Rollout Plan

- **Stage 1** shipped nothing (unreleased refactor inside chopdiff); it is the correctness
  gate for everything after.
- **Stage 2** publishes flexdoc on its own version line (starting at `0.1.0`), then makes
  chopdiff's first release depending on the external flexdoc — **breaking**, because the
  document-model import paths moved (`chopdiff.docs.*` → `flexdoc.*`); flagged in chopdiff's
  `CHANGELOG.md` with a migration note under the pre-1.0 minor-bump policy.
- Each repo keeps its own supply-chain `exclude-newer` cool-off, kept in sync.

## Resolved Decisions

- **One-wheel / two-import-root layout for Stage 1** (maintainer-confirmed).
- **The cut is forced by the import graph.** `{docs, html, util}` → flexdoc; `transforms` →
  chopdiff; only `divs` was a free choice.
- **`divs/` stays in chopdiff** (chunking matches chopdiff's identity; keeps flexdoc a
  minimal closed core), to migrate into flexdoc as the synthetic layer at Stage 4.
- **Whole-module moves, no logic edits**; `token_diffs` travels into flexdoc as a consequence
  of the `docs` cycle.
- **No backward-compatibility shims.** The break lands intentionally in chopdiff's Stage 2
  release.
- **Boundary enforced by a dependency-free test** (Stage 1); structural in Stage 2.
- **flexdoc dependency partition verified** (11 runtime deps; `selectolax` confirmed via the
  function-local import; `typing-extensions` declared directly; `simplemma` excluded).
- **Supply-chain config mirrors chopdiff** (same cutoff and exceptions; idna fixed to 3.15
  via `uv lock --upgrade-package`; audit gate ignores only the pip advisory).

## Open Questions

- **flexdoc distribution name.** Confirm `flexdoc` is available on PyPI before Step 4; if
  taken, pick an alternative. Also resolve the textdoc-spec §13 name collision (Stage 5).
- **`token_diffs` long-term home.** Forced into flexdoc for v1 by the `docs` cycle; whether
  to relocate the diff primitives later is open (Stage 3).
- **flexdoc's top-level public API.** Submodule-only today; whether to add curated root-level
  re-exports is a Stage 3/Stage 5 decision.
- **Depth and backends of the grammar/language axis**, **which "other structures" to
  prioritize**, and **the extension-interface shape** — flexdoc Stage-3 decisions, constrained
  by the light-core and supply-chain principles.

## References

- Design of record: [`docs/textdoc-spec.md`](../../../textdoc-spec.md).
- Unified document model (houses the model flexdoc owns; synthetic layer = its Phase 3 / this
  plan's Stage 4): [`plan-2026-05-29-unified-document-model.md`](plan-2026-05-29-unified-document-model.md).
- Markdown-layer completion (prerequisite):
  [`plan-2026-06-11-structural-metadata.md`](plan-2026-06-11-structural-metadata.md).
- Layered-model backing:
  [`research-2026-05-30-multilayer-parsing.md`](../../research/research-2026-05-30-multilayer-parsing.md)
  and [`research-2026-05-30-span-references.md`](../../research/research-2026-05-30-span-references.md).

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
