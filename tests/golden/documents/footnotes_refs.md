---
name: footnotes_refs
description: Reference-style links and footnotes, whose identities resolve across blocks
  but whose rendered text has no contiguous source span (span=None handling). Includes a
  multi-block footnote definition (continuation paragraph and list) to pin that the
  whole continuation stays one footnote block.
---
# References

See the [docs][d] and the [spec][s] for details.[^note]

A bare autolink: <https://auto.example> and a plain https://bare.example URL.[^multi]

[d]: https://docs.example
[s]: https://spec.example "Spec Title"

[^note]: A footnote definition with its own text.

[^multi]: First paragraph of a multi-block footnote.

    Second paragraph, indented under the definition.

    - a list inside the footnote
    - with two items
