# Feature: Robust Logical Word Metrics

**Date:** 2026-07-13

**Author:** Joshua Levy (with Codex assistance)

**Status:** In Review

**Implementation status:** The implementation and follow-up naming revision are
complete. Draft PR #18 documents the final contract, its GitHub Actions matrix is
passing, and it is ready for review.

## Overview

Add a language- and format-robust logical word measure based on GitHub issue #16.
Define `TextUnit.words` as the normalized logical-word measure and add
`TextUnit.raw_words` for the existing whitespace-delimited behavior. Core structured
fields and summaries keep the concise `words` name, with docstrings and public docs
making its logical semantics and divergence from ordinary word counts explicit. Use
this measure for section trees, token estimates, and usage guidance.

This is an intentional pre-1.0 semantic break. The old behavior remains available under
the accurate `raw_words` name, while `TextUnit.words` changes meaning. The
character-based token-estimator configuration is not retained as an alias.

## Goals

- Preserve the existing whitespace-delimited word measure as `raw_words`.
- Define `words` as the logical measure, which remains close to raw words for ordinary
  spaced prose and stays useful for CJK, code, URLs, math, and machine-readable text.
- Base tokenizer-free token estimates on logical words rather than raw character count.
- Make default document and section metrics use logical words without hiding the raw
  measure from callers that specifically need it.
- Keep the implementation deterministic, dependency-free, linear-time, and consistent
  across supported Python versions.
- Document and test the breaking API changes and the algorithm's known limitations.

## Non-Goals

- Linguistic word segmentation or dictionary-based tokenization.
- Exact token counts for any model or provider.
- Per-language, per-script, per-format, or per-model correction tables.
- Tokenizer dependencies or network-based validation in the test suite.
- A separate `TextUnit.logical_words` member or a compatibility alias for
  `CHARS_PER_TOKEN` or the `chars_per_token` keyword.
- A package release or version tag; this change is prepared for the next pre-1.0 minor
  release.

## Background

`TextUnit.words` currently counts whitespace-delimited tokens after converting HTML to
plain text. This is intuitive for ordinary English prose but undercounts unspaced CJK
text and long symbolic runs by an order of magnitude. `estimate_tokens()` independently
uses characters divided by 3.8, which is format- and language-sensitive in a different
way.

Issue #16 proposes a logical word count with two rules:

1. Non-whitespace Unicode characters with East Asian Width `W` or `F` contribute 0.5
   logical word each.
2. Remaining text is split on whitespace. Its raw word count is clamped so average
   characters per logical word stays between 3 and 6.

The linked validation compares ten natural languages, source code, minified JavaScript,
CSV, JSON, and mixed Markdown. Tokens per logical word span 1.36–2.24 for the tested
o200k-family model, versus a 24-fold spread for raw words and a threefold spread for
characters divided by four. A multiplier of 1.6 is a useful model-free default for
prose, CJK, code, and Markdown, while punctuation-dense machine formats remain a known
underestimate.

The reference implementations need two clarifications before adoption:

- Python's `round()` uses ties-to-even while JavaScript's `Math.round()` uses half-up,
  so the published implementations disagree whenever the unrounded count ends in 0.5.
  FlexDoc defines non-negative half-up rounding explicitly.
- U+3000 IDEOGRAPHIC SPACE is both whitespace and East Asian Width `F`. Counting every
  wide character would make some whitespace-only strings nonzero. FlexDoc counts only
  non-whitespace wide characters, preserving the stated empty/whitespace-only contract.

## Design

### Approach

Implement the word-counting primitives in a small utility module with named constants
and no external dependencies. `TextUnit` applies both word measures to the same
`html_to_plaintext()` projection, so `raw_words` exactly preserves the former `words`
behavior and `words` measures normalized reader-visible content.

`estimate_tokens()` applies logical word counting directly to the supplied serialized
text. This intentionally includes Markdown or HTML syntax that an LLM would receive,
while `TextUnit.words` continues to measure the plain-text projection used for
human-facing word counts.

Logical word counts are computed over the complete paragraph, document, or section
text rather than summed from already-rounded sentence counts. This avoids rounding
error amplification while retaining sentence-level sizing for callers that explicitly
request it.

### Components

#### Word-Counting Utility

Add `flexdoc.util.word_count` with:

- `MIN_CHARS_PER_LOGICAL_WORD = 3.0`
- `MAX_CHARS_PER_LOGICAL_WORD = 6.0`
- `WIDE_CHAR_LOGICAL_WORD_WEIGHT = 0.5`
- `raw_word_count(text)` for a direct whitespace split
- `logical_word_count(text, ...)` for the weighted and clamped measure

The configurable bounds must be positive and ordered, and the wide-character weight
must be non-negative. Invalid configuration raises `ValueError` with the invalid
contract stated in the message.

Given non-whitespace wide count `wide`, remaining whitespace-delimited token count
`raw`, and the sum of their character lengths `chars`:

```
clamped = max(chars / 6, min(chars / 3, raw))
logical_words = floor(wide * 0.5 + clamped + 0.5)
```

The final expression is explicit half-up rounding for a non-negative measure.

#### Text Units and Aggregation

Change `TextUnit` as follows:

- retain `words = "words"` but change it to logical-word semantics
- add `raw_words = "raw_words"`
- do not add a separate `logical_words` member

`size(text, raw_words)` retains the former `words` implementation exactly.
`size(text, words)` applies `logical_word_count()` to the same HTML-to-plain-text
projection. `Sentence`, `Paragraph`, `FlexDoc`, `Section`, `seek_to_sent()`, filtered
documents, frontmatter exclusion, and section rollups support both units.

The standard `size_summary()` and debug-report fields remain `words`, and their
docstrings define them as logical counts. `section_size_tree()` defaults to
`TextUnit.words`. Raw counts remain available through explicit
`size(TextUnit.raw_words)` calls.

With the default bounds, logical and raw counts are equal for non-wide text averaging
3–6 non-whitespace characters per whitespace-delimited word. A longer average raises
the logical count, a shorter average lowers it, and wide/fullwidth characters contribute
0.5 each. Long identifiers, URLs, short-token sequences, Markdown, code, and symbolic
runs can therefore differ from an ordinary expected count. Non-visible HTML markup is
removed by the shared plain-text projection before either `TextUnit` word measure.

#### Token Estimation

Replace `CHARS_PER_TOKEN = 3.8` with `TOKENS_PER_LOGICAL_WORD = 1.6` and change
`estimate_tokens(text, tokens_per_logical_word=...)` to:

```
ceil(logical_word_count(text) * tokens_per_logical_word)
```

The multiplier must be positive; invalid values raise `ValueError`. Empty text remains
zero. Documentation must state that this is an approximate o200k-family-centered
default, that punctuation-dense machine formats can run near 2.2 tokens per logical
word, and that exact model limits require that model's tokenizer.

#### Reading Time

`format_read_time()` remains numerically unchanged because it accepts a count rather
than source text. Its documentation and examples recommend passing
`TextUnit.words`; at 225 logical words per minute, the 0.5 CJK weight implies
about 450 wide characters per minute.

#### Documentation and Behavioral Artifacts

Update the root API example, README, usage guide, FlexDoc specification, changelog,
TODO/spec index, docstrings, tests, and golden reports. Examples that mean normalized
content volume use `words`; examples that demonstrate the literal historical
measure use `raw_words` explicitly.

### API Changes

- Added `TextUnit.raw_words`.
- Changed `TextUnit.words` from whitespace-delimited to logical-word semantics.
- Did not add a separate `TextUnit.logical_words` member.
- Added `raw_word_count()` and `logical_word_count()` under `flexdoc.util`.
- Added logical-word constants under `flexdoc.util`.
- Replaced `CHARS_PER_TOKEN` with `TOKENS_PER_LOGICAL_WORD`.
- Replaced the `estimate_tokens(..., chars_per_token=...)` keyword with
  `tokens_per_logical_word`.
- Changed the values behind `size_summary()`, `section_size_tree()`, and debug-report
  `words` fields from raw to logical words without lengthening their field names.

### Backward Compatibility

- **Code types, methods, and function signatures:** DO NOT MAINTAIN. Change the
  `TextUnit.words` semantics and token-estimator configuration directly; update all
  in-repository callers.
- **Library APIs:** DO NOT MAINTAIN. This is a documented pre-1.0 minor-version semantic
  break, with `raw_words` providing the old measurement under its accurate name.
- **Server APIs:** N/A.
- **File formats:** N/A. Checked-in golden debug reports change intentionally and are
  regenerated and reviewed.
- **Database schemas:** N/A.

## Implementation Plan

### Phase 1: Metrics and API Migration

- [x] Add failing behavior tests for raw/logical counts, cross-language rounding,
  whitespace, bounds, mixed content, and token estimates.
- [x] Implement the word-counting utility and logical-word-based token estimator.
- [x] Define `TextUnit.words` as logical and add `raw_words` across every size grain,
  ensuring aggregate counts are computed before rounding.
- [x] Switch summaries, section-tree defaults, debug reports, and reading-time guidance
  to logical words.
- [x] Update all callers, public examples, API/spec documentation, changelog, and work
  tracking references.
- [x] Regenerate golden reports and review every changed field.

## Testing Strategy

- Unit-test ordinary English equality, long identifiers and URLs, CJK and mixed text,
  wide whitespace, explicit half-up ties, empty input, custom bounds/weights, and
  invalid configuration.
- Unit-test token estimates for empty, ordinary prose, CJK, code-like text, custom
  multipliers, and invalid multipliers.
- Integration-test `Sentence`, `Paragraph`, `FlexDoc`, and `Section` raw/logical sizes;
  whole-document rounding; frontmatter exclusion; `seek_to_sent()` support; summary
  wording; section-tree defaults; and root API usage.
- Regenerate deterministic golden reports and review the summary and section metric
  diffs rather than accepting them mechanically.
- Run focused tests during red-green-refactor cycles, then `make lint`, `make test`,
  `make build`, and an isolated wheel import/API smoke test.
- Let the pull request's full Python 3.11–3.14 and representative macOS CI matrix pass
  before marking the work complete.

## Rollout Plan

Land as one pre-1.0 feature PR targeting `main`, with the breaking changes called out in
the changelog and PR body. The next release should be a minor version (expected 0.4.0),
not a 0.3.x patch. Downstream callers that want the new normalized measure continue to
use `TextUnit.words`; callers requiring literal whitespace-delimited behavior migrate
to `TextUnit.raw_words`.

## Open Questions

None. The user direction and pre-1.0 compatibility policy resolve the naming and
default-behavior decisions; issue #16 and its validation resolve the initial constants.

## References

- GitHub issue [#16](https://github.com/jlevy/flexdoc/issues/16)
- [Logical Word Count research and validation](https://gist.github.com/jlevy/0d6d87885f6d85f31440e58b8cfce663)
- [Document-metrics use case](plan-2026-06-13-metrics-use-case.md)
- [FlexDoc stabilization roadmap](plan-2026-07-09-flexdoc-stabilization-roadmap.md)
- `docs/flexdoc-spec.md` sizing and token-estimation contract

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
