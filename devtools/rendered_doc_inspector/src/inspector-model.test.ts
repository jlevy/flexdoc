import { describe, expect, test } from 'bun:test'

import {
  buildLayerForest,
  normalizeThemeMode,
  resolveHoverTrail,
  resolveThemeMode,
  scrollTopToReveal,
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
    children: [],
    sourceSpan: { start: 0, end: 80 },
    attrs: { title: 'Notes' },
    text: '# Notes',
  },
  {
    id: 'paragraph',
    kind: 'paragraph',
    layer: 'markdown',
    parent: null,
    children: ['link'],
    sourceSpan: { start: 10, end: 70 },
    attrs: {},
    text: 'A source-anchored link.',
  },
  {
    id: 'textual-paragraph',
    kind: 'paragraph',
    layer: 'textual',
    parent: null,
    children: ['sentence'],
    sourceSpan: { start: 10, end: 70 },
    attrs: {},
    text: 'A source-anchored link.',
  },
  {
    id: 'sentence',
    kind: 'sentence',
    layer: 'textual',
    parent: 'textual-paragraph',
    children: [],
    sourceSpan: { start: 10, end: 70 },
    attrs: {},
    text: 'A source-anchored link.',
  },
  {
    id: 'link',
    kind: 'link',
    layer: 'markdown',
    parent: 'paragraph',
    children: [],
    sourceSpan: { start: 22, end: 44 },
    attrs: { text: 'source-anchored link' },
    text: '[source-anchored link](https://example.com)',
  },
]

describe('rendered inspector model', () => {
  test('builds each DocGraph layer as an ordered containment forest', () => {
    const markdownForest = buildLayerForest(nodes, 'markdown')
    const textualForest = buildLayerForest(nodes, 'textual')

    expect(markdownForest.map(root => ({
      id: root.node.id,
      children: root.children.map(child => child.node.id),
    }))).toEqual([{ id: 'paragraph', children: ['link'] }])
    expect(textualForest.map(root => ({
      id: root.node.id,
      children: root.children.map(child => child.node.id),
    }))).toEqual([{ id: 'textual-paragraph', children: ['sentence'] }])

    const danglingNodes = nodes.map(node => (
      node.id === 'paragraph' ? { ...node, children: ['missing'] } : node
    ))
    expect(() => buildLayerForest(danglingNodes, 'markdown')).toThrow(
      'DocGraph markdown layer references missing child missing.',
    )
  })

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

  test('normalizes and resolves persisted theme preferences', () => {
    expect(normalizeThemeMode('light')).toBe('light')
    expect(normalizeThemeMode('dark')).toBe('dark')
    expect(normalizeThemeMode('unexpected')).toBe('system')
    expect(resolveThemeMode('system', true)).toBe('dark')
    expect(resolveThemeMode('system', false)).toBe('light')
    expect(resolveThemeMode('light', true)).toBe('light')
  })

  test('keeps visible source selections still and centers hidden selections', () => {
    expect(scrollTopToReveal({
      contentHeight: 600,
      currentScrollTop: 0,
      targetHeight: 20,
      targetTop: 50,
      viewportHeight: 200,
    })).toBe(0)
    expect(scrollTopToReveal({
      contentHeight: 600,
      currentScrollTop: 0,
      targetHeight: 20,
      targetTop: 300,
      viewportHeight: 200,
    })).toBe(210)
    expect(scrollTopToReveal({
      contentHeight: 600,
      currentScrollTop: 0,
      targetHeight: 20,
      targetTop: 590,
      viewportHeight: 200,
    })).toBe(400)
  })
})
