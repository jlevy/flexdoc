---
name: heading_edges
description: Adversarial heading layouts - a heading preceded by an HTML-comment marker
  with no blank line, a setext heading, a level jump, headings nested in a blockquote and a
  list item (which must not start document sections), a fully glued (tight) heading/body
  pair, and a duplicate top-level title. Exercises sections()/toc() and section content.
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

# Top

A second top-level section with a duplicate title (sections are identified by span, not title).

# Tight outer
Intro glued directly under the tight outer heading with no blank line.
## Tight inner
Body glued directly under the tight inner heading with no blank line.
