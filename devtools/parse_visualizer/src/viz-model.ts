import type {
  LayerName,
  SourceSpan,
  VizData,
  VizNode,
  VizSelection,
  VizWordtok,
} from './viz-types.ts'

export type VizIndex = {
  nodes: Map<string, VizNode>
  wordtoks: Map<string, VizWordtok>
}

/** Build constant-time node and wordtok lookups for synchronized views. */
export function buildVizIndex(data: VizData): VizIndex {
  return {
    nodes: new Map(data.nodes.map(node => [node.id, node])),
    wordtoks: new Map(data.wordtoks.map(wordtok => [wordtok.id, wordtok])),
  }
}

export function spanContains(container: SourceSpan, subject: SourceSpan): boolean {
  return container.start <= subject.start && subject.end <= container.end
}

export function spansOverlap(left: SourceSpan, right: SourceSpan): boolean {
  return left.start < right.end && right.start < left.end
}

/** Resolve either selection kind to the canonical code-point span. */
export function selectionSpan(index: VizIndex, selection: VizSelection): SourceSpan {
  if (selection.type === 'node') {
    const node = index.nodes.get(selection.id)
    if (node?.source_span === null || node?.source_span === undefined) {
      throw new Error(`Selected node has no source span: ${selection.id}`)
    }
    return node.source_span
  }
  const wordtok = index.wordtoks.get(selection.id)
  if (wordtok === undefined) throw new Error(`Unknown wordtok: ${selection.id}`)
  return wordtok.source_span
}

/** Return all source containers from narrowest to widest. */
export function containingNodes(data: VizData, span: SourceSpan): VizNode[] {
  return data.nodes
    .filter(node => node.source_span !== null && spanContains(node.source_span, span))
    .sort((left, right) => {
      const leftWidth = left.source_span!.end - left.source_span!.start
      const rightWidth = right.source_span!.end - right.source_span!.start
      return leftWidth - rightWidth || left.layer.localeCompare(right.layer) || left.id.localeCompare(right.id)
    })
}

/** Return source-overlapping nodes in deterministic document order. */
export function overlappingNodes(data: VizData, span: SourceSpan): VizNode[] {
  return data.nodes
    .filter(node => node.source_span !== null && spansOverlap(node.source_span, span))
    .sort((left, right) => {
      const start = left.source_span!.start - right.source_span!.start
      return start || right.source_span!.end - left.source_span!.end || left.id.localeCompare(right.id)
    })
}

export function nodeDepth(node: VizNode, index: VizIndex): number {
  let depth = 0
  let parentId = node.parent
  const seen = new Set<string>()
  while (parentId !== null && !seen.has(parentId)) {
    seen.add(parentId)
    const parent = index.nodes.get(parentId)
    if (parent === undefined || parent.layer !== node.layer) break
    depth += 1
    parentId = parent.parent
  }
  return depth
}

export function nodesForLayer(data: VizData, layer: LayerName): VizNode[] {
  return data.nodes.filter(node => node.layer === layer && node.source_span !== null)
}

export function rootNodesForLayer(data: VizData, index: VizIndex, layer: LayerName): VizNode[] {
  return nodesForLayer(data, layer).filter(node => {
    if (node.parent === null) return true
    return index.nodes.get(node.parent)?.layer !== layer
  })
}

export function nodeLabel(node: VizNode): string {
  const title = node.attrs['title']
  if (typeof title === 'string' && title.length > 0) return `${node.kind}: ${title}`
  const text = node.attrs['text']
  if (typeof text === 'string' && text.length > 0) return `${node.kind}: ${text}`
  return node.kind
}

export function lineAndColumn(lineStarts: number[], offset: number): { line: number; column: number } {
  let low = 0
  let high = lineStarts.length
  while (low < high) {
    const middle = Math.floor((low + high) / 2)
    if (lineStarts[middle]! <= offset) low = middle + 1
    else high = middle
  }
  const lineIndex = Math.max(0, low - 1)
  return { line: lineIndex + 1, column: offset - lineStarts[lineIndex]! + 1 }
}

/** Find the narrowest node that covers a span, with an optional layer preference. */
export function narrowestNode(
  data: VizData,
  span: SourceSpan,
  preferredLayer: LayerName | null,
): VizNode | null {
  const matches = containingNodes(data, span)
  if (preferredLayer !== null) {
    const preferred = matches.find(node => node.layer === preferredLayer)
    if (preferred !== undefined) return preferred
  }
  return matches[0] ?? null
}
