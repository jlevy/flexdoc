/** A half-open span in FlexDoc's Unicode code-point coordinate space. */
export interface SourceSpan {
  start: number
  end: number
}

/** The browser-facing subset of a DocGraph node used by the inspector. */
export interface InspectorNode {
  id: string
  kind: string
  layer: string
  parent: string | null
  children: string[]
  sourceSpan: SourceSpan | null
  attrs: Record<string, unknown>
  text: string | null
}

/** One node in a layer-specific DocGraph containment tree. */
export interface InspectorTreeNode {
  node: InspectorNode
  children: InspectorTreeNode[]
}

export interface SourceSplit {
  before: string
  active: string
  after: string
}

interface ScrollRevealMetrics {
  contentHeight: number
  currentScrollTop: number
  targetHeight: number
  targetTop: number
  viewportHeight: number
}

export type ResolvedTheme = 'light' | 'dark'
export type ThemeMode = 'system' | ResolvedTheme

const INLINE_KINDS = new Set([
  'code_span',
  'footnote_ref',
  'image',
  'inline_html',
  'link',
  'link_ref_def',
])

const TEXTUAL_KIND_RANK: Readonly<Record<string, number>> = {
  paragraph: 0,
  sentence: 1,
}

const THEME_MODES = new Set<ThemeMode>(['system', 'light', 'dark'])

/** Build one layer's ordered containment forest from DocGraph parent/child links. */
export function buildLayerForest(
  nodes: readonly InspectorNode[],
  layer: string,
): InspectorTreeNode[] {
  const layerNodes = nodes.filter(node => node.layer === layer)
  const nodesById = new Map(layerNodes.map(node => [node.id, node]))
  const visiting = new Set<string>()
  const visited = new Set<string>()

  const buildTree = (nodeId: string): InspectorTreeNode => {
    const node = nodesById.get(nodeId)
    if (node === undefined) {
      throw new Error(`DocGraph ${layer} layer references missing child ${nodeId}.`)
    }
    if (visiting.has(nodeId)) {
      throw new Error(`DocGraph ${layer} layer contains a cycle at ${nodeId}.`)
    }
    if (visited.has(nodeId)) {
      throw new Error(`DocGraph ${layer} layer contains ${nodeId} more than once.`)
    }

    visiting.add(nodeId)
    const children = node.children.map(childId => {
      const child = nodesById.get(childId)
      if (child !== undefined && child.parent !== nodeId) {
        throw new Error(`DocGraph child ${childId} does not point back to ${nodeId}.`)
      }
      return buildTree(childId)
    })
    visiting.delete(nodeId)
    visited.add(nodeId)
    return { node, children }
  }

  const forest = layerNodes
    .filter(node => node.parent === null)
    .map(node => buildTree(node.id))
  if (visited.size !== layerNodes.length) {
    const disconnected = layerNodes.find(node => !visited.has(node.id))
    throw new Error(
      `DocGraph ${layer} layer contains disconnected node ${disconnected?.id ?? 'unknown'}.`,
    )
  }
  return forest
}

/** Normalize persisted or DOM-provided theme state. */
export function normalizeThemeMode(value: string | null | undefined): ThemeMode {
  if (value !== null && value !== undefined && THEME_MODES.has(value as ThemeMode)) {
    return value as ThemeMode
  }
  return 'system'
}

/** Resolve an explicit or system-relative theme to its concrete palette. */
export function resolveThemeMode(mode: ThemeMode, systemPrefersDark: boolean): ResolvedTheme {
  if (mode !== 'system') return mode
  return systemPrefersDark ? 'dark' : 'light'
}

/** Return a scroller position that reveals a target without moving visible content. */
export function scrollTopToReveal(metrics: ScrollRevealMetrics): number {
  const targetBottom = metrics.targetTop + metrics.targetHeight
  const viewportBottom = metrics.currentScrollTop + metrics.viewportHeight
  if (metrics.targetTop >= metrics.currentScrollTop && targetBottom <= viewportBottom) {
    return metrics.currentScrollTop
  }

  const centeredScrollTop = metrics.targetTop
    + metrics.targetHeight / 2
    - metrics.viewportHeight / 2
  const maximumScrollTop = Math.max(0, metrics.contentHeight - metrics.viewportHeight)
  return Math.min(Math.max(0, centeredScrollTop), maximumScrollTop)
}

/** Return whether `outer` fully contains `inner`. */
export function spansContain(outer: SourceSpan, inner: SourceSpan): boolean {
  return outer.start <= inner.start && inner.end <= outer.end
}

/** Split exact source around a selected code-point span. */
export function splitSourceForSpan(source: string, span: SourceSpan): SourceSplit {
  const codePoints = Array.from(source)
  return {
    before: codePoints.slice(0, span.start).join(''),
    active: codePoints.slice(span.start, span.end).join(''),
    after: codePoints.slice(span.end).join(''),
  }
}

/**
 * Resolve one rendered hover into a readable cross-layer containment trail.
 *
 * Document sections come first, then Markdown block ancestry, textual paragraph and
 * sentence containment, and finally the precise inline construct under the pointer.
 */
export function resolveHoverTrail(
  nodes: readonly InspectorNode[],
  span: SourceSpan,
  directNodeId: string | null,
): InspectorNode[] {
  const containing = nodes.filter(
    node => node.sourceSpan !== null && spansContain(node.sourceSpan, span),
  )
  const documentNodes = sortedOuterFirst(
    containing.filter(node => node.layer === 'document'),
  )
  const markdownBlocks = sortedOuterFirst(
    containing.filter(node => node.layer === 'markdown' && !INLINE_KINDS.has(node.kind)),
  )
  const textualNodes = [...containing]
    .filter(node => node.layer === 'textual')
    .sort((left, right) => {
      const spanOrder = spanLength(right) - spanLength(left)
      if (spanOrder !== 0) return spanOrder
      return (TEXTUAL_KIND_RANK[left.kind] ?? Number.MAX_SAFE_INTEGER)
        - (TEXTUAL_KIND_RANK[right.kind] ?? Number.MAX_SAFE_INTEGER)
    })
  const inlineNodes = sortedOuterFirst(
    containing.filter(node => node.layer === 'markdown' && INLINE_KINDS.has(node.kind)),
  )
  const directNode = directNodeId === null ? undefined : nodes.find(node => node.id === directNodeId)

  const ordered = [...documentNodes, ...markdownBlocks, ...textualNodes, ...inlineNodes]
  const unique = ordered.filter(
    (node, index, allNodes) => allNodes.findIndex(candidate => candidate.id === node.id) === index,
  )
  if (directNode !== undefined && INLINE_KINDS.has(directNode.kind)) {
    return [...unique.filter(node => node.id !== directNode.id), directNode]
  }
  return unique
}

function sortedOuterFirst(nodes: readonly InspectorNode[]): InspectorNode[] {
  return [...nodes].sort((left, right) => spanLength(right) - spanLength(left))
}

function spanLength(node: InspectorNode): number {
  return node.sourceSpan === null ? 0 : node.sourceSpan.end - node.sourceSpan.start
}
