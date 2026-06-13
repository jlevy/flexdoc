---
name: heading_edges
description: Adversarial heading layouts - a heading preceded by an HTML-comment marker
  with no blank line, a setext heading, a level jump, and headings nested in a blockquote
  and a list item (which must not start document sections). Exercises sections()/toc().
---
# Top

Intro under the top heading.

<!-- a marker comment with no blank line before the next heading -->
## Marker preceded

Body under the marker-preceded heading.

Setext title
============

#### Jumped to level four

> ## Heading inside a blockquote (not a document section)
>
> Quoted body.

- ### Heading inside a list item (not a document section)
- second item
