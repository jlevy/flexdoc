## What's Changed

This release stabilizes the pre-1.0 API boundary from the 2026-07 pre-promotion design review ([senior engineering review](https://github.com/jlevy/flexdoc/blob/main/docs/project/review/senior-engineering-review-flexdoc-2026-07.md), PRs #9 and #10). It fixes correctness bugs in source-coordinate handling and anchoring, and settles the remaining pre-1.0 API decisions so later releases can add annotation and synthetic-layer mechanisms without reopening the foundation. Because it changes documented behavior on a pre-1.0 library, it bumps the minor version (per the pre-1.0 rule in `docs/publishing.md`).

### Bug Fixes

**CRLF input no longer corrupts the structural views**

marko computes block positions against LF-only text, so `\r` in the input desynchronized every structural span (`blocks()`, `sections()`, `base_blocks()`, `links()`, `prose_text()`, the node table) from `source_text`, silently garbling content. `from_text` now normalizes `\r\n` and lone `\r` to `\n` and retains the normalized string as `source_text`, so all layers share one offset space. Callers anchoring offsets to an external CRLF original must normalize it the same way first.

**Markdown constructs inside frontmatter can no longer swallow the body**

The shared parse previously included the frontmatter region, so e.g. a YAML block scalar containing a code fence opened a fenced block spanning the rest of the document, leaving `blocks()` empty. The frontmatter region is now blanked out of the shared parse (offsets preserved); frontmatter remains a non-content region.

**`resolve()` no longer guesses on ambiguous quotes**

A `SpanRef` quote that occurs multiple times with no disambiguating prefix/suffix (or a tied context score) now resolves to `None` instead of silently anchoring to the first occurrence. A context-free position hint also cannot select a duplicate, and a zero-width quote (`exact=""`) resolves to `None`.

**`collect(overlaps=...)` treats empty intervals as empty**

A degenerate `[x, x)` region now overlaps nothing, matching half-open interval semantics; point queries use `(x, x + 1)`.

**Render helpers harden their HTML output**

`render_node_attrs` attribute-escapes `node.id`, and `wrap_with_node_attrs` validates the tag name (raising `ValueError`), matching the `flexdoc.html` tag helpers.

### Breaking Changes

Made cleanly with no compatibility aliases, given the preview (pre-1.0) status:

- **`SpanRef` owns its public resolution API** — call `ref.resolve(source_text)` / `ref.resolve_and_update(source_text)`; the generic `resolve` / `resolve_and_update` names are no longer promoted from `flexdoc.docs`.
- **`flexdoc.docs` now promotes the document model only** — word-token/search and diff/mapping names moved to their owning modules (`flexdoc.docs.wordtoks`, `search_tokens`, `token_diffs`, `token_mapping`).
- **Recursive `collect()` includes inline descendants by default** — `inline` is now tri-state; pass `inline=False` for the previous block-only recursive result.
- **`Paragraph.heading_level` / `Paragraph.heading_title` are properties** — remove the `()` from calls.
- **`NAVIGABLE_LINK_FORMS` replaces `TRUE_LINK_FORMS`** — no alias retained.
- **`TextUnit` is a `StrEnum`** — `TextUnit.words == "words"` now holds; only `str()`/equality behavior changes.
- **Cached structural views are mutation-safe** — `Block` is frozen, `Block.children` and `TableInfo.alignments` are tuples, and `sections()` returns isolated copies; direct `Block` construction must pass child tuples.

### Other Changes

- `graph()` accepts any `Set` for `include`/`detail`, so plain `set` literals type-check.
- Frontmatter delimiters tolerate trailing horizontal whitespace.
- The dependency lock is refreshed under the 14-day cool-off (cutoff 2026-06-26) with no per-package exceptions or audit ignores; CI runs `pip-audit` clean.
- The OS-independent classifier is backed by a macOS CI job (Python 3.13 full lint/test gate on `macos-latest`).
- Local release preparation is tag-aware, preventing a tagless clone from producing a `0.0.1.devN` artifact.

### Full Changelog

https://github.com/jlevy/flexdoc/compare/v0.2.0...v0.3.0
