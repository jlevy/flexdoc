## What's Changed

This release adds the portable reference and annotation layer from the 2026-07 TextRef design cycle plus cross-language logical word metrics, finalized under an independent senior release review ([review and breaking-change catalog](https://github.com/jlevy/flexdoc/blob/main/docs/project/review/senior-engineering-review-v0.4-release-2026-07.md); PRs #18, #20, #21). Because it changes documented behavior on a pre-1.0 library, it bumps the minor version (per the pre-1.0 rule in `docs/publishing.md`). If you depend on an unbounded `flexdoc>=0.3.0`, review the breaking changes below or pin `<0.4` before upgrading.

### New Features

**Native TextRef integration**

Strict `DocRef`/`TextRef` values identify whole documents, spans, points, and semantic sections with canonical JSON and reversible `textref:0.1` URIs. `FlexDoc.references()` binds a document locator to one source snapshot: it maps every locatable public value (`for_target`, `for_span`, `for_point`, `for_section`), resolves references with typed outcomes on independent document/source-validation/selector axes (resolution never silently picks a duplicate), retrieves structured line-window context, and renders deterministic annotation views for humans and LLMs. Span quote evidence is configurable per context or per span; compact exact-less spans stay bound to one source hash.

**Consumer-owned annotations**

`TextAnnotation` and the one-document `AnnotationSet` sidecar round-trip strict JSON and safe YAML, and every sidecar entry is validated through the complete TextRef evidence contract at parse time. `DocGraph/v0.2` embeds a matching sidecar after verifying its document and source hash against the snapshot, and bounds-checks embedded positions. Committed JSON Schemas ship for both formats in the wheel.

**Cross-language logical word metrics**

`TextUnit.words` now measures normalized word-equivalent volume across natural language, CJK text, source code, URLs, and punctuation-dense content. `TextUnit.raw_words` and `raw_word_count()` keep literal whitespace counting, and `logical_word_count()` exposes the dependency-free primitive. See the [logical-word definition and validation](https://gist.github.com/jlevy/0d6d87885f6d85f31440e58b8cfce663).

### Breaking Changes

Made cleanly with no compatibility aliases, given the pre-1.0 status. Full catalog with rationales and migrations: [review doc §4](https://github.com/jlevy/flexdoc/blob/main/docs/project/review/senior-engineering-review-v0.4-release-2026-07.md).

- **`FlexDoc.graph()` requires a document locator** — `doc.graph()` becomes `doc.graph(document="path/or/id.md")`; `build_doc_graph()` and the debug helpers `doc_graph_yaml()`/`dump_views()` take the same argument. Every serialized graph is now self-identifying.
- **DocGraph wire contract v0.1 → v0.2** — `schema` is `"DocGraph/v0.2"`; `source.document` is required; the unqualified `source.sha256` field is replaced by algorithm-qualified `source.source_hash` (shared with TextRef); models are strict (unknown fields rejected, frozen, strict types) and validate node references, span/text consistency, and annotation bounds.
- **`TextUnit.words` is logical** — it matches raw counts for ordinary non-wide prose but differs for wide/fullwidth scripts, URLs, code, and symbolic content; use `TextUnit.raw_words` for the previous whitespace-split behavior. Ripples through `size()`, `size_summary()`, `section_size_tree()`, and debug reports.
- **Token estimates scale logical words** — `estimate_tokens(text, tokens_per_logical_word=1.6)` replaces the `chars_per_token` parameter, and `TOKENS_PER_LOGICAL_WORD` replaces `CHARS_PER_TOKEN`; estimates change numerically even at defaults.
- **`format_read_time()` takes logical word counts** — same signature; the default rate corresponds to roughly 450 CJK characters per minute under the default wide-character weight.
- **Pinned outputs change** — regenerate any golden DocGraph/report snapshots (schema string, `source` block, and `words` fields).

### Full Changelog

https://github.com/jlevy/flexdoc/compare/v0.3.0...v0.4.0
