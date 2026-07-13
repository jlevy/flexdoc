import { describe, expect, test } from 'bun:test'

import {
  resolveHoverTrail,
  splitSourceForSpan,
  spansContain,
  type InspectorNode,
} from './inspector-model'

const nodes: InspectorNode[] = [
  {
    id: 'section',
    kind: 'section',
    layer: 'document',
    parent: null,
    sourceSpan: { start: 0, end: 80 },
    attrs: { title: 'Notes' },
  },
  {
    id: 'paragraph',
    kind: 'paragraph',
    layer: 'markdown',
    parent: null,
    sourceSpan: { start: 10, end: 70 },
    attrs: {},
  },
  {
    id: 'textual-paragraph',
    kind: 'paragraph',
    layer: 'textual',
    parent: null,
    sourceSpan: { start: 10, end: 70 },
    attrs: {},
  },
  {
    id: 'sentence',
    kind: 'sentence',
    layer: 'textual',
    parent: 'textual-paragraph',
    sourceSpan: { start: 10, end: 70 },
    attrs: {},
  },
  {
    id: 'link',
    kind: 'link',
    layer: 'markdown',
    parent: 'paragraph',
    sourceSpan: { start: 22, end: 44 },
    attrs: { text: 'source-anchored link' },
  },
]

describe('rendered inspector model', () => {
  test('builds a human nesting trail with the direct inline node last', () => {
    const trail = resolveHoverTrail(nodes, { start: 22, end: 44 }, 'link')

    expect(trail.map(node => node.id)).toEqual([
      'section',
      'paragraph',
      'textual-paragraph',
      'sentence',
      'link',
    ])
  })

  test('splits source without changing a code-point span', () => {
    const source = 'alpha beta gamma'

    expect(splitSourceForSpan(source, { start: 6, end: 10 })).toEqual({
      before: 'alpha ',
      active: 'beta',
      after: ' gamma',
    })
    expect(spansContain({ start: 0, end: source.length }, { start: 6, end: 10 })).toBe(true)

    expect(splitSourceForSpan('a😀b', { start: 1, end: 2 })).toEqual({
      before: 'a',
      active: '😀',
      after: 'b',
    })
  })
})
