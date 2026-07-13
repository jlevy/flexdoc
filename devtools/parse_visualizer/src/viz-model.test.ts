import { describe, expect, test } from 'bun:test'

import {
  buildVizIndex,
  containingNodes,
  lineAndColumn,
  selectionSpan,
  spansOverlap,
} from './viz-model.ts'
import type { VizData } from './viz-types.ts'

const data: VizData = {
  schema: 'DocGraph/v0.1',
  title: 'test',
  source: {
    format: 'markdown',
    offset_unit: 'unicode_code_points',
    sha256: 'test',
    text: '# T\n\nWord.',
  },
  nodes: [
    {
      id: 'section',
      kind: 'section',
      layer: 'document',
      parent: null,
      children: [],
      source_span: { start: 0, end: 10 },
      attrs: {},
      text: null,
    },
    {
      id: 'sentence',
      kind: 'sentence',
      layer: 'textual',
      parent: null,
      children: [],
      source_span: { start: 5, end: 10 },
      attrs: {},
      text: null,
    },
  ],
  roots: ['section', 'sentence'],
  views: { toc: [], blocks: [], links: [], paragraphs: [], sentences: [] },
  wordtoks: [
    {
      id: 'word',
      value: 'Word',
      exact: 'Word',
      kind: 'word',
      source_span: { start: 5, end: 9 },
      utf16_span: { start: 5, end: 9 },
    },
  ],
  line_starts: [0, 4, 5],
}

describe('shared visualization model', () => {
  test('resolves selections and cross-layer containers', () => {
    const index = buildVizIndex(data)
    const span = selectionSpan(index, { type: 'wordtok', id: 'word' })

    expect(span).toEqual({ start: 5, end: 9 })
    expect(containingNodes(data, span).map(node => node.id)).toEqual(['sentence', 'section'])
  })

  test('uses half-open overlap and source line coordinates', () => {
    expect(spansOverlap({ start: 0, end: 5 }, { start: 5, end: 8 })).toBeFalse()
    expect(spansOverlap({ start: 0, end: 6 }, { start: 5, end: 8 })).toBeTrue()
    expect(lineAndColumn(data.line_starts, 7)).toEqual({ line: 3, column: 3 })
  })
})
