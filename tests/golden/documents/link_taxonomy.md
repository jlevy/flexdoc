---
name: link_taxonomy
description: Every link form - inline, reference, shortcut reference, autolink, bare URL,
  inline image, reference image, and used and unused reference definitions - to exercise
  LinkForm classification, images(), and reference-definition surfacing. Linked images
  `[![alt](i)](u)` are a deliberate non-goal; see the metrics-use-case plan.
---
# Link taxonomy

An [inline link](https://inline.example) and a [reference link][ref] and a [shortcut].

An autolink <https://auto.example> and a bare URL https://bare.example in prose.

An inline image ![inline alt](https://img.example/a.png) and a reference image
![ref alt][img].

[ref]: https://reference.example "Reference title"
[shortcut]: https://shortcut.example
[img]: https://img.example/c.png
[unused]: https://unused.example
