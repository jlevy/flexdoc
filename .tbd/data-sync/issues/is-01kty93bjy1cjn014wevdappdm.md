---
type: is
id: is-01kty93bjy1cjn014wevdappdm
title: Rename TextDoc -> FlexDoc (class, module, spec) via repren
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies: []
created_at: 2026-06-12T16:02:04.510Z
updated_at: 2026-06-12T16:08:56.501Z
closed_at: 2026-06-12T16:08:56.501Z
close_reason: TextDoc->FlexDoc via uvx repren (3 literal passes); module flex_doc.py; spec renamed flexdoc-spec.md + section 13 name reclaimed; schema regenerated; goldens untouched
---
Maintainer-decided 2026-06-12. Hard cut, no alias: class TextDoc->FlexDoc; module text_doc.py->flex_doc.py (tests test_text_doc.py follows); docs/textdoc-spec.md->flexdoc-spec.md retitled 'FlexDoc and DocGraph' with section 13 rewritten to deliberately reclaim the FlexDoc name from the abandoned BlockDoc/SectionDoc branch; ci.yml wheel-smoke updated; CHANGELOG migration notes reworked coherently. History docs (review, copied plans/briefs) keep TextDoc prose; only spec path refs update. Goldens/DocGraph wire format untouched (verified name-free). Use uvx repren@latest.
