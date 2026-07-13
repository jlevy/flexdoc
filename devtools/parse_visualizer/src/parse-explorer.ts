import cytoscape, {
  type Core,
  type ElementDefinition,
  type EventObject,
  type NodeSingular,
} from 'cytoscape'
import { hierarchy, partition, type HierarchyRectangularNode } from 'd3-hierarchy'
import { layoutWithLines, prepareWithSegments, type LayoutCursor } from '@chenglou/pretext'

import rawData from '../generated/parse-data.json'
import {
  buildVizIndex,
  containingNodes,
  lineAndColumn,
  narrowestNode,
  nodeDepth,
  nodeLabel,
  nodesForLayer,
  overlappingNodes,
  rootNodesForLayer,
  selectionSpan,
  spanContains,
  spansOverlap,
  type VizIndex,
} from './viz-model.ts'
import type {
  LayerName,
  SourceSpan,
  VizData,
  VizMode,
  VizNode,
  VizSelection,
  VizWordtok,
} from './viz-types.ts'

const data = rawData as VizData
const index = buildVizIndex(data)
const inlineKinds = new Set(['code_span', 'footnote_ref', 'image', 'inline_html', 'link', 'link_ref_def'])
const layers: LayerName[] = ['document', 'markdown', 'textual']

type ExplorerState = {
  mode: VizMode
  selection: VizSelection
  hierarchyLayer: 'document' | 'markdown'
  hierarchyShape: 'icicle' | 'sunburst'
  pretextWidth: number
  showCrossLayerEdges: boolean
}

type ModeDefinition = {
  label: string
  kicker: string
  description: string
}

const modeDefinitions: Record<VizMode, ModeDefinition> = {
  tracks: {
    label: 'Tracks',
    kicker: 'Intervals',
    description: 'A genome-browser-style overview: every layer aligned to canonical source offsets.',
  },
  source: {
    label: 'Source lens',
    kicker: 'Exact text',
    description: 'The source itself is the map. Select a token to reveal every structure containing it.',
  },
  hierarchy: {
    label: 'Hierarchy',
    kicker: 'D3 partition',
    description: 'Icicle and sunburst experiments for one honest within-layer tree at a time.',
  },
  flow: {
    label: 'Layer flow',
    kicker: 'Parallel sets',
    description: 'Source-positioned columns expose how sections, Markdown, and prose units correspond.',
  },
  graph: {
    label: 'Graph',
    kicker: 'Cytoscape',
    description: 'Topology-first debugging for parents, children, and inferred cross-layer containment.',
  },
  pretext: {
    label: 'Pretext wrap',
    kicker: 'Line geometry',
    description: 'Width-independent text analysis projected into exact wrapped source ranges.',
  },
  microscope: {
    label: 'Microscope',
    kicker: 'Local detail',
    description: 'A compact sentence/token view surrounded by its cross-layer structural context.',
  },
}

const defaultNode =
  data.nodes.find(node => node.layer === 'markdown' && node.kind === 'paragraph') ?? data.nodes[0]
if (defaultNode === undefined) throw new Error('Visualization data has no nodes')

const state: ExplorerState = {
  mode: 'tracks',
  selection: { type: 'node', id: defaultNode.id },
  hierarchyLayer: 'markdown',
  hierarchyShape: 'icicle',
  pretextWidth: 680,
  showCrossLayerEdges: true,
}

const appElement = document.getElementById('app')
if (appElement === null) throw new Error('#app not found')
const app = appElement

app.innerHTML = `
  <div class="app-shell">
    <header class="app-header">
      <div>
        <p class="eyebrow">FlexDoc developer laboratory</p>
        <h1 id="document-title"></h1>
        <p class="header-copy">Seven synchronized experiments over one DocGraph. Every mark resolves to the same source span.</p>
      </div>
      <div class="metrics" id="metrics"></div>
    </header>
    <nav class="mode-tabs" id="mode-tabs" aria-label="Visualization modes"></nav>
    <main class="workspace">
      <section class="visual-panel" aria-labelledby="mode-title">
        <div class="mode-head">
          <div>
            <div class="mode-kicker" id="mode-kicker"></div>
            <h2 class="mode-title" id="mode-title"></h2>
            <p class="mode-description" id="mode-description"></p>
          </div>
          <div class="mode-controls" id="mode-controls"></div>
        </div>
        <div class="visual-host" id="visual-host"></div>
      </section>
      <aside class="inspector" id="inspector" aria-label="Selected parse element"></aside>
    </main>
    <div class="legend">
      <span class="legend-item"><span class="layer-dot" style="--layer-color: var(--document)"></span>Document</span>
      <span class="legend-item"><span class="layer-dot" style="--layer-color: var(--markdown)"></span>Markdown</span>
      <span class="legend-item"><span class="layer-dot" style="--layer-color: var(--textual)"></span>Textual</span>
      <span class="legend-item"><span class="layer-dot" style="--layer-color: var(--wordtok)"></span>Wordtok</span>
    </div>
  </div>
`

const documentTitle = requiredElement('document-title')
const metrics = requiredElement('metrics')
const modeTabs = requiredElement('mode-tabs')
const modeKicker = requiredElement('mode-kicker')
const modeTitle = requiredElement('mode-title')
const modeDescription = requiredElement('mode-description')
const modeControls = requiredElement('mode-controls')
const visualHost = requiredElement('visual-host')
const inspector = requiredElement('inspector')

let graph: Core | null = null

documentTitle.textContent = data.title
renderMetrics()
renderTabs()
render()

function requiredElement(id: string): HTMLElement {
  const element = document.getElementById(id)
  if (element === null) throw new Error(`#${id} not found`)
  return element
}

function layerColor(layer: LayerName | 'wordtok'): string {
  return `var(--${layer})`
}

function setLayerColor(element: HTMLElement | SVGElement, layer: LayerName | 'wordtok'): void {
  element.style.setProperty('--layer-color', layerColor(layer))
}

function renderMetrics(): void {
  const values: [string, string][] = [
    [data.source.text.length.toLocaleString(), 'code points'],
    [data.nodes.length.toLocaleString(), 'nodes'],
    [data.wordtoks.length.toLocaleString(), 'wordtoks'],
    [data.views.sentences.length.toLocaleString(), 'sentences'],
  ]
  metrics.replaceChildren(
    ...values.map(([value, label]) => {
      const metric = document.createElement('div')
      metric.className = 'metric'
      const valueElement = document.createElement('span')
      valueElement.className = 'metric-value'
      valueElement.textContent = value
      const labelElement = document.createElement('span')
      labelElement.className = 'metric-label'
      labelElement.textContent = label
      metric.append(valueElement, labelElement)
      return metric
    }),
  )
}

function renderTabs(): void {
  const modes = Object.entries(modeDefinitions) as [VizMode, ModeDefinition][]
  modeTabs.replaceChildren(
    ...modes.map(([mode, definition]) => {
      const button = document.createElement('button')
      button.className = 'mode-tab'
      button.type = 'button'
      button.setAttribute('role', 'tab')
      button.setAttribute('aria-selected', String(state.mode === mode))
      button.textContent = definition.label
      button.addEventListener('click', () => {
        state.mode = mode
        renderTabs()
        render()
      })
      return button
    }),
  )
}

function render(): void {
  graph?.destroy()
  graph = null
  const definition = modeDefinitions[state.mode]
  modeKicker.textContent = definition.kicker
  modeTitle.textContent = definition.label
  modeDescription.textContent = definition.description
  modeControls.replaceChildren()
  visualHost.replaceChildren()

  switch (state.mode) {
    case 'tracks':
      renderTracks()
      break
    case 'source':
      renderSourceLens()
      break
    case 'hierarchy':
      renderHierarchy()
      break
    case 'flow':
      renderLayerFlow()
      break
    case 'graph':
      renderGraph()
      break
    case 'pretext':
      renderPretext()
      break
    case 'microscope':
      renderMicroscope()
      break
    default: {
      const exhaustive: never = state.mode
      throw new Error(`Unhandled visualization mode: ${exhaustive}`)
    }
  }
  renderInspector()
}

function setSelection(selection: VizSelection): void {
  state.selection = selection
  render()
}

function isSelected(selection: VizSelection): boolean {
  return selection.type === state.selection.type && selection.id === state.selection.id
}

function selectedSpan(): SourceSpan {
  return selectionSpan(index, state.selection)
}

function renderTracks(): void {
  type TrackItem = { id: string; label: string; span: SourceSpan; depth: number; selection: VizSelection }
  type TrackGroup = { label: string; layer: LayerName | 'wordtok'; items: TrackItem[] }

  const markdownBlocks = data.nodes.filter(
    node => node.layer === 'markdown' && node.source_span !== null && !inlineKinds.has(node.kind),
  )
  const markdownInline = data.nodes.filter(
    node => node.layer === 'markdown' && node.source_span !== null && inlineKinds.has(node.kind),
  )
  const nodeItems = (nodes: VizNode[]): TrackItem[] =>
    nodes.map(node => ({
      id: node.id,
      label: nodeLabel(node),
      span: node.source_span!,
      depth: nodeDepth(node, index),
      selection: { type: 'node', id: node.id },
    }))

  const groups: TrackGroup[] = [
    { label: 'Document', layer: 'document', items: nodeItems(nodesForLayer(data, 'document')) },
    { label: 'Markdown', layer: 'markdown', items: nodeItems(markdownBlocks) },
    { label: 'Inline', layer: 'markdown', items: nodeItems(markdownInline) },
    { label: 'Textual', layer: 'textual', items: nodeItems(nodesForLayer(data, 'textual')) },
    {
      label: 'Wordtoks',
      layer: 'wordtok',
      items: data.wordtoks.map(wordtok => ({
        id: wordtok.id,
        label: `${wordtok.kind}: ${wordtok.value}`,
        span: wordtok.source_span,
        depth: 0,
        selection: { type: 'wordtok', id: wordtok.id },
      })),
    },
  ]

  const stack = document.createElement('div')
  stack.className = 'track-stack'
  for (const group of groups) {
    const lane = document.createElement('div')
    lane.className = 'lane'
    setLayerColor(lane, group.layer)
    const label = document.createElement('div')
    label.className = 'lane-label'
    label.textContent = `${group.label} · ${group.items.length}`
    const body = document.createElement('div')
    body.className = 'lane-body'
    const maxDepth = Math.max(0, ...group.items.map(item => item.depth))
    body.style.setProperty('--lane-depth', String(maxDepth))
    for (const item of group.items) {
      const widthPercent = ((item.span.end - item.span.start) / data.source.text.length) * 100
      const button = document.createElement('button')
      button.className = `segment-button${isSelected(item.selection) ? ' is-selected' : ''}`
      button.type = 'button'
      button.style.setProperty('--start', `${(item.span.start / data.source.text.length) * 100}%`)
      button.style.setProperty('--width', `${widthPercent}%`)
      button.style.setProperty('--depth', String(item.depth))
      button.textContent = group.layer !== 'wordtok' && widthPercent >= 1.5 ? item.label : ''
      button.setAttribute('aria-label', `${item.label}, ${item.span.start}:${item.span.end}`)
      button.addEventListener('click', () => setSelection(item.selection))
      body.appendChild(button)
    }
    lane.append(label, body)
    stack.appendChild(lane)
  }
  const axis = document.createElement('div')
  axis.className = 'track-axis'
  axis.innerHTML = `<span>0</span><span>25%</span><span>50%</span><span>75%</span><span>${data.source.text.length}</span>`
  stack.appendChild(axis)
  visualHost.appendChild(stack)
}

function renderSourceLens(): void {
  const source = document.createElement('pre')
  source.className = 'source-lens'
  const span = selectedSpan()
  for (const wordtok of data.wordtoks) {
    const selection: VizSelection = { type: 'wordtok', id: wordtok.id }
    const button = document.createElement('button')
    const contained = spansOverlap(wordtok.source_span, span)
    button.className = `wordtok-button${isSelected(selection) ? ' is-selected' : ''}${contained ? ' is-contained' : ''}`
    button.type = 'button'
    button.dataset['tokenKind'] = wordtok.kind
    button.textContent = wordtok.exact
    const containers = containingNodes(data, wordtok.source_span)
    button.setAttribute(
      'aria-label',
      `${wordtok.kind} ${wordtok.source_span.start}:${wordtok.source_span.end}; ${containers.map(nodeLabel).join(', ')}`,
    )
    button.addEventListener('click', () => setSelection(selection))
    source.appendChild(button)
  }
  visualHost.appendChild(source)
}

type HierarchyDatum = {
  node: VizNode | null
  name: string
  children: HierarchyDatum[]
}

function hierarchyDatum(node: VizNode, layer: LayerName): HierarchyDatum {
  return {
    node,
    name: nodeLabel(node),
    children: node.children
      .map(childId => index.nodes.get(childId))
      .filter((child): child is VizNode => child !== undefined && child.layer === layer)
      .map(child => hierarchyDatum(child, layer)),
  }
}

function renderHierarchy(): void {
  const layerSelect = document.createElement('select')
  layerSelect.setAttribute('aria-label', 'Hierarchy layer')
  for (const layer of ['markdown', 'document'] as const) {
    const option = document.createElement('option')
    option.value = layer
    option.selected = state.hierarchyLayer === layer
    option.textContent = layer === 'markdown' ? 'Markdown tree' : 'Section tree'
    layerSelect.appendChild(option)
  }
  layerSelect.addEventListener('change', () => {
    state.hierarchyLayer = layerSelect.value as 'document' | 'markdown'
    render()
  })

  const shapeSelect = document.createElement('select')
  shapeSelect.setAttribute('aria-label', 'Hierarchy shape')
  for (const shape of ['icicle', 'sunburst'] as const) {
    const option = document.createElement('option')
    option.value = shape
    option.selected = state.hierarchyShape === shape
    option.textContent = shape === 'icicle' ? 'Icicle' : 'Sunburst'
    shapeSelect.appendChild(option)
  }
  shapeSelect.addEventListener('change', () => {
    state.hierarchyShape = shapeSelect.value as 'icicle' | 'sunburst'
    render()
  })
  modeControls.append(layerSelect, shapeSelect)

  const roots = rootNodesForLayer(data, index, state.hierarchyLayer)
  const datum: HierarchyDatum = {
    node: null,
    name: state.hierarchyLayer,
    children: roots.map(node => hierarchyDatum(node, state.hierarchyLayer)),
  }
  const root = hierarchy(datum, item => item.children).sum(item => {
    if (item.children.length > 0 || item.node?.source_span === null || item.node === null) return 0
    return Math.max(1, item.node.source_span.end - item.node.source_span.start)
  })

  if (state.hierarchyShape === 'icicle') renderIcicle(root)
  else renderSunburst(root)
}

function renderIcicle(root: ReturnType<typeof hierarchy<HierarchyDatum>>): void {
  const width = 960
  const rowHeight = 64
  const height = Math.max(320, (root.height + 1) * rowHeight)
  const laidOut = partition<HierarchyDatum>().size([width, height])(root)
  const svg = svgElement('svg')
  svg.classList.add('hierarchy-svg')
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`)
  svg.setAttribute('role', 'img')
  svg.setAttribute('aria-label', `${state.hierarchyLayer} icicle hierarchy`)

  for (const item of laidOut.descendants().slice(1)) {
    const node = item.data.node
    if (node === null) continue
    const group = svgElement('g')
    group.classList.add('hierarchy-cell')
    if (state.selection.type === 'node' && state.selection.id === node.id) group.classList.add('is-selected')
    setLayerColor(group, node.layer)
    const rect = svgElement('rect')
    rect.setAttribute('x', String(item.x0 + 1))
    rect.setAttribute('y', String(item.y0 + 1))
    rect.setAttribute('width', String(Math.max(1, item.x1 - item.x0 - 2)))
    rect.setAttribute('height', String(Math.max(1, item.y1 - item.y0 - 2)))
    const title = svgElement('title')
    title.textContent = `${nodeLabel(node)} · ${node.source_span?.start}:${node.source_span?.end}`
    rect.appendChild(title)
    group.appendChild(rect)
    if (item.x1 - item.x0 > 54) {
      const text = svgElement('text')
      text.setAttribute('x', String(item.x0 + 6))
      text.setAttribute('y', String(item.y0 + 21))
      text.textContent = truncate(nodeLabel(node), Math.max(6, Math.floor((item.x1 - item.x0) / 7)))
      group.appendChild(text)
    }
    group.addEventListener('click', () => setSelection({ type: 'node', id: node.id }))
    svg.appendChild(group)
  }
  visualHost.appendChild(svg)
}

function renderSunburst(root: ReturnType<typeof hierarchy<HierarchyDatum>>): void {
  const size = 720
  const radius = 330
  const laidOut = partition<HierarchyDatum>().size([Math.PI * 2, radius])(root)
  const svg = svgElement('svg')
  svg.classList.add('hierarchy-svg')
  svg.setAttribute('viewBox', `0 0 ${size} ${size}`)
  svg.setAttribute('role', 'img')
  svg.setAttribute('aria-label', `${state.hierarchyLayer} sunburst hierarchy`)
  const center = svgElement('g')
  center.setAttribute('transform', `translate(${size / 2} ${size / 2})`)
  svg.appendChild(center)

  for (const item of laidOut.descendants().slice(1)) {
    const node = item.data.node
    if (node === null) continue
    const group = svgElement('g')
    group.classList.add('hierarchy-cell')
    if (state.selection.type === 'node' && state.selection.id === node.id) group.classList.add('is-selected')
    setLayerColor(group, node.layer)
    const path = svgElement('path')
    path.setAttribute('d', annularPath(item))
    const title = svgElement('title')
    title.textContent = `${nodeLabel(node)} · ${node.source_span?.start}:${node.source_span?.end}`
    path.appendChild(title)
    group.appendChild(path)
    group.addEventListener('click', () => setSelection({ type: 'node', id: node.id }))
    center.appendChild(group)
  }
  visualHost.appendChild(svg)
}

function annularPath(item: HierarchyRectangularNode<HierarchyDatum>): string {
  const start = item.x0 - Math.PI / 2
  const end = Math.min(item.x1 - Math.PI / 2, start + Math.PI * 2 - 0.00001)
  const inner = item.y0
  const outer = item.y1 - 1
  const largeArc = end - start > Math.PI ? 1 : 0
  const outerStart = polarPoint(outer, start)
  const outerEnd = polarPoint(outer, end)
  const innerEnd = polarPoint(inner, end)
  const innerStart = polarPoint(inner, start)
  return [
    `M ${outerStart.x} ${outerStart.y}`,
    `A ${outer} ${outer} 0 ${largeArc} 1 ${outerEnd.x} ${outerEnd.y}`,
    `L ${innerEnd.x} ${innerEnd.y}`,
    `A ${inner} ${inner} 0 ${largeArc} 0 ${innerStart.x} ${innerStart.y}`,
    'Z',
  ].join(' ')
}

function polarPoint(radius: number, angle: number): { x: number; y: number } {
  return { x: radius * Math.cos(angle), y: radius * Math.sin(angle) }
}

function renderLayerFlow(): void {
  const width = 1000
  const height = 660
  const columnX: Record<LayerName, number> = { document: 70, markdown: 420, textual: 770 }
  const nodeWidth = 160
  const nodesByLayer = new Map<LayerName, VizNode[]>([
    ['document', nodesForLayer(data, 'document')],
    [
      'markdown',
      data.nodes.filter(node => node.layer === 'markdown' && node.source_span !== null && !inlineKinds.has(node.kind)),
    ],
    ['textual', nodesForLayer(data, 'textual')],
  ])
  const positions = new Map<string, { x: number; y: number }>()
  for (const layer of layers) {
    for (const node of nodesByLayer.get(layer) ?? []) {
      const span = node.source_span!
      positions.set(node.id, {
        x: columnX[layer],
        y: 46 + ((span.start + span.end) / 2 / data.source.text.length) * (height - 90),
      })
    }
  }

  const edges: { source: VizNode; target: VizNode }[] = []
  const connect = (sourceLayer: LayerName, targetLayer: LayerName): void => {
    for (const target of nodesByLayer.get(targetLayer) ?? []) {
      const targetSpan = target.source_span!
      const source = (nodesByLayer.get(sourceLayer) ?? [])
        .filter(candidate => spanContains(candidate.source_span!, targetSpan))
        .sort((left, right) => {
          const leftWidth = left.source_span!.end - left.source_span!.start
          const rightWidth = right.source_span!.end - right.source_span!.start
          return leftWidth - rightWidth
        })[0]
      if (source !== undefined) edges.push({ source, target })
    }
  }
  connect('document', 'markdown')
  connect('markdown', 'textual')

  const svg = svgElement('svg')
  svg.classList.add('flow-svg')
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`)
  svg.setAttribute('role', 'img')
  svg.setAttribute('aria-label', 'Cross-layer containment flow')

  for (const layer of layers) {
    const label = svgElement('text')
    label.setAttribute('x', String(columnX[layer]))
    label.setAttribute('y', '22')
    label.setAttribute('fill', 'currentColor')
    label.setAttribute('font-size', '12')
    label.textContent = `${layer} · ${nodesByLayer.get(layer)?.length ?? 0}`
    svg.appendChild(label)
  }

  const selected = selectedSpan()
  for (const edge of edges) {
    const source = positions.get(edge.source.id)!
    const target = positions.get(edge.target.id)!
    const path = svgElement('path')
    path.classList.add('flow-link')
    if (spansOverlap(edge.target.source_span!, selected)) path.classList.add('is-selected')
    const x1 = source.x + nodeWidth
    const x2 = target.x
    const middle = (x1 + x2) / 2
    path.setAttribute('d', `M ${x1} ${source.y} C ${middle} ${source.y}, ${middle} ${target.y}, ${x2} ${target.y}`)
    svg.appendChild(path)
  }

  for (const layer of layers) {
    for (const node of nodesByLayer.get(layer) ?? []) {
      const position = positions.get(node.id)!
      const group = svgElement('g')
      group.classList.add('flow-node')
      if (state.selection.type === 'node' && state.selection.id === node.id) group.classList.add('is-selected')
      setLayerColor(group, layer)
      const rect = svgElement('rect')
      rect.setAttribute('x', String(position.x))
      rect.setAttribute('y', String(position.y - 8))
      rect.setAttribute('width', String(nodeWidth))
      rect.setAttribute('height', '16')
      rect.setAttribute('rx', '4')
      group.appendChild(rect)
      const text = svgElement('text')
      text.setAttribute('x', String(position.x + 5))
      text.setAttribute('y', String(position.y + 3))
      text.textContent = truncate(nodeLabel(node), 22)
      group.appendChild(text)
      group.addEventListener('click', () => setSelection({ type: 'node', id: node.id }))
      svg.appendChild(group)
    }
  }
  visualHost.appendChild(svg)
}

function renderGraph(): void {
  const label = document.createElement('label')
  const checkbox = document.createElement('input')
  checkbox.type = 'checkbox'
  checkbox.checked = state.showCrossLayerEdges
  checkbox.addEventListener('change', () => {
    state.showCrossLayerEdges = checkbox.checked
    render()
  })
  label.append(checkbox, document.createTextNode(' Cross-layer edges'))
  modeControls.appendChild(label)

  const container = document.createElement('div')
  container.className = 'graph-canvas'
  visualHost.appendChild(container)

  const graphNodes = data.nodes.filter(node => node.source_span !== null)
  const elements: ElementDefinition[] = graphNodes.map(node => ({
    data: { id: node.id, label: node.kind, layer: node.layer },
    position: graphPosition(node),
    selected: state.selection.type === 'node' && state.selection.id === node.id,
  }))
  for (const node of graphNodes) {
    if (node.parent !== null && index.nodes.get(node.parent)?.layer === node.layer) {
      elements.push({ data: { id: `parent:${node.parent}:${node.id}`, source: node.parent, target: node.id, relation: 'parent' } })
    }
  }
  if (state.showCrossLayerEdges) {
    for (const node of graphNodes) {
      const previousLayer = node.layer === 'textual' ? 'markdown' : node.layer === 'markdown' ? 'document' : null
      if (previousLayer === null) continue
      const containerNode = narrowestNode(data, node.source_span!, previousLayer)
      if (containerNode !== null && containerNode.id !== node.id) {
        elements.push({
          data: {
            id: `contains:${containerNode.id}:${node.id}`,
            source: containerNode.id,
            target: node.id,
            relation: 'contains',
          },
        })
      }
    }
  }

  const computed = getComputedStyle(app)
  graph = cytoscape({
    container,
    elements,
    layout: { name: 'preset', fit: true, padding: 36 },
    minZoom: 0.25,
    maxZoom: 4,
    style: [
      {
        selector: 'node',
        style: {
          'background-color': computed.getPropertyValue('--surface-raised').trim(),
          'border-color': computed.getPropertyValue('--border').trim(),
          'border-width': 1,
          color: computed.getPropertyValue('--foreground').trim(),
          label: 'data(label)',
          'font-size': 9,
          height: 22,
          shape: 'round-rectangle',
          'text-valign': 'center',
          width: 82,
        },
      },
      {
        selector: 'node[layer = "document"]',
        style: { 'border-color': computed.getPropertyValue('--document').trim(), 'border-width': 2 },
      },
      {
        selector: 'node[layer = "markdown"]',
        style: { 'border-color': computed.getPropertyValue('--markdown').trim(), 'border-width': 2 },
      },
      {
        selector: 'node[layer = "textual"]',
        style: { 'border-color': computed.getPropertyValue('--textual').trim(), 'border-width': 2 },
      },
      {
        selector: 'node:selected',
        style: {
          'background-color': computed.getPropertyValue('--selection').trim(),
          'border-color': computed.getPropertyValue('--selection').trim(),
          color: computed.getPropertyValue('--selection-ink').trim(),
        },
      },
      {
        selector: 'edge[relation = "parent"]',
        style: {
          'curve-style': 'bezier',
          'line-color': computed.getPropertyValue('--border').trim(),
          opacity: 0.7,
          width: 1,
        },
      },
      {
        selector: 'edge[relation = "contains"]',
        style: {
          'curve-style': 'bezier',
          'line-color': computed.getPropertyValue('--muted').trim(),
          'line-style': 'dashed',
          opacity: 0.35,
          width: 1,
        },
      },
    ],
  })
  graph.on('tap', 'node', (event: EventObject) => {
    const node = event.target as NodeSingular
    setSelection({ type: 'node', id: node.id() })
  })
}

function graphPosition(node: VizNode): { x: number; y: number } {
  const layerX: Record<LayerName, number> = { document: 100, markdown: 430, textual: 760 }
  const span = node.source_span!
  return {
    x: layerX[node.layer] + nodeDepth(node, index) * 24,
    y: 30 + ((span.start + span.end) / 2 / data.source.text.length) * 890,
  }
}

function renderPretext(): void {
  const widthLabel = document.createElement('label')
  widthLabel.textContent = `Text width ${state.pretextWidth}px`
  const width = document.createElement('input')
  width.type = 'range'
  width.min = '280'
  width.max = '900'
  width.value = String(state.pretextWidth)
  width.addEventListener('input', () => {
    state.pretextWidth = Number(width.value)
    render()
  })
  modeControls.append(widthLabel, width)

  const font = '13px Menlo, "DejaVu Sans Mono", monospace'
  const prepared = prepareWithSegments(data.source.text, font, { whiteSpace: 'pre-wrap' })
  const result = layoutWithLines(prepared, state.pretextWidth - 58, 22)
  const segmentStarts: number[] = []
  let segmentOffset = 0
  for (const segment of prepared.segments) {
    segmentStarts.push(segmentOffset)
    segmentOffset += segment.length
  }
  const stage = document.createElement('div')
  stage.className = 'pretext-stage'
  stage.style.width = `${state.pretextWidth}px`
  const selected = selectedSpan()
  for (const line of result.lines) {
    const startUtf16 = cursorToUtf16(prepared.segments, segmentStarts, line.start)
    const endUtf16 = cursorToUtf16(prepared.segments, segmentStarts, line.end)
    const lineSpan = {
      start: utf16ToCodePoint(data.source.text, startUtf16),
      end: utf16ToCodePoint(data.source.text, endUtf16),
    }
    const row = document.createElement('button')
    row.className = `pretext-line${spansOverlap(lineSpan, selected) ? ' is-selected' : ''}`
    row.type = 'button'
    const range = document.createElement('span')
    range.className = 'line-range'
    range.textContent = `${lineSpan.start}:${lineSpan.end}`
    const text = document.createElement('span')
    text.className = 'line-text'
    text.textContent = line.text.length === 0 ? '↵' : line.text
    row.append(range, text)
    row.addEventListener('click', () => {
      const node = narrowestNode(data, lineSpan, null)
      if (node !== null) setSelection({ type: 'node', id: node.id })
    })
    stage.appendChild(row)
  }
  visualHost.appendChild(stage)
}

function cursorToUtf16(segments: string[], starts: number[], cursor: LayoutCursor): number {
  if (cursor.segmentIndex >= segments.length) {
    const last = segments.at(-1)
    const lastStart = starts.at(-1)
    return last === undefined || lastStart === undefined ? 0 : lastStart + last.length
  }
  const segment = segments[cursor.segmentIndex]!
  const segmentStart = starts[cursor.segmentIndex]!
  if (cursor.graphemeIndex === 0) return segmentStart
  const graphemes = Array.from(new Intl.Segmenter(undefined, { granularity: 'grapheme' }).segment(segment))
  const part = graphemes[cursor.graphemeIndex]
  return part === undefined ? segmentStart + segment.length : segmentStart + part.index
}

function utf16ToCodePoint(text: string, utf16Offset: number): number {
  return Array.from(text.slice(0, utf16Offset)).length
}

function renderMicroscope(): void {
  const selection = selectedSpan()
  const containers = containingNodes(data, selection)
  const textualRegion =
    containers.find(node => node.layer === 'textual' && node.kind === 'sentence') ??
    containers.find(node => node.layer === 'textual' && node.kind === 'paragraph')
  const localSpan = textualRegion?.source_span ?? selection
  const outerSpan = containers.at(-1)?.source_span ?? localSpan

  const context = document.createElement('div')
  context.className = 'microscope-context'
  for (const node of containers.slice().reverse()) {
    const nodeSpan = node.source_span!
    const band = document.createElement('div')
    band.className = 'context-band'
    setLayerColor(band, node.layer)
    const label = document.createElement('div')
    label.className = 'context-layer'
    label.textContent = node.kind
    const bar = document.createElement('div')
    bar.className = 'context-bar'
    const marker = document.createElement('button')
    marker.className = 'context-span'
    marker.type = 'button'
    marker.style.setProperty('--start', `${((nodeSpan.start - outerSpan.start) / Math.max(1, outerSpan.end - outerSpan.start)) * 100}%`)
    marker.style.setProperty('--width', `${((nodeSpan.end - nodeSpan.start) / Math.max(1, outerSpan.end - outerSpan.start)) * 100}%`)
    marker.setAttribute('aria-label', `${nodeLabel(node)} ${nodeSpan.start}:${nodeSpan.end}`)
    marker.addEventListener('click', () => setSelection({ type: 'node', id: node.id }))
    bar.appendChild(marker)
    band.append(label, bar)
    context.appendChild(band)
  }

  const cloud = document.createElement('div')
  cloud.className = 'token-cloud'
  for (const wordtok of data.wordtoks.filter(item => spansOverlap(item.source_span, localSpan))) {
    const tokenSelection: VizSelection = { type: 'wordtok', id: wordtok.id }
    const button = document.createElement('button')
    button.className = `token-chip${isSelected(tokenSelection) ? ' is-selected' : ''}`
    button.type = 'button'
    button.dataset['tokenKind'] = wordtok.kind
    button.textContent = visibleWordtok(wordtok)
    button.setAttribute('aria-label', `${wordtok.kind} ${wordtok.source_span.start}:${wordtok.source_span.end}`)
    button.addEventListener('click', () => setSelection(tokenSelection))
    cloud.appendChild(button)
  }
  visualHost.append(context, cloud)
}

function visibleWordtok(wordtok: VizWordtok): string {
  if (wordtok.kind !== 'whitespace') return wordtok.exact
  return wordtok.exact.replaceAll(' ', '␠').replaceAll('\t', '⇥').replaceAll('\n', '↵')
}

function renderInspector(): void {
  const span = selectedSpan()
  const start = lineAndColumn(data.line_starts, span.start)
  const end = lineAndColumn(data.line_starts, span.end)
  const containers = containingNodes(data, span)
  const overlaps = overlappingNodes(data, span)
  const selectedNode = state.selection.type === 'node' ? index.nodes.get(state.selection.id) : undefined
  const selectedWordtok = state.selection.type === 'wordtok' ? index.wordtoks.get(state.selection.id) : undefined
  const heading = selectedNode === undefined ? selectedWordtok?.kind ?? 'wordtok' : nodeLabel(selectedNode)
  const kind = selectedNode === undefined ? `wordtok · ${selectedWordtok?.kind}` : `${selectedNode.layer} · ${selectedNode.id}`
  const source = data.source.text.slice(span.start, span.end)
  const attrs = selectedNode?.attrs ?? {
    normalized: selectedWordtok?.value,
    exact: selectedWordtok?.exact,
    utf16_span: selectedWordtok?.utf16_span,
  }

  inspector.replaceChildren()
  const title = document.createElement('h2')
  title.textContent = heading
  const subtitle = document.createElement('p')
  subtitle.className = 'inspector-kind'
  subtitle.textContent = kind
  inspector.append(title, subtitle)
  inspector.appendChild(inspectorSection('Source span', `${span.start}:${span.end} · L${start.line}:${start.column} → L${end.line}:${end.column}`))

  const sourceSection = document.createElement('section')
  sourceSection.className = 'inspector-section'
  const sourceLabel = document.createElement('span')
  sourceLabel.className = 'inspector-label'
  sourceLabel.textContent = 'Exact source'
  const quote = document.createElement('pre')
  quote.className = 'source-quote'
  quote.textContent = source
  sourceSection.append(sourceLabel, quote)
  inspector.appendChild(sourceSection)

  const attributeSection = document.createElement('section')
  attributeSection.className = 'inspector-section'
  const attributeLabel = document.createElement('span')
  attributeLabel.className = 'inspector-label'
  attributeLabel.textContent = 'Attributes'
  const attributeList = document.createElement('pre')
  attributeList.className = 'source-quote'
  attributeList.textContent = JSON.stringify(attrs, null, 2)
  attributeSection.append(attributeLabel, attributeList)
  inspector.appendChild(attributeSection)

  const containerSection = document.createElement('section')
  containerSection.className = 'inspector-section'
  const containerLabel = document.createElement('span')
  containerLabel.className = 'inspector-label'
  containerLabel.textContent = `Containers · ${containers.length}`
  containerSection.appendChild(containerLabel)
  for (const node of containers) containerSection.appendChild(inspectorNodeButton(node))
  inspector.appendChild(containerSection)

  const overlapSection = document.createElement('section')
  overlapSection.className = 'inspector-section'
  const overlapLabel = document.createElement('span')
  overlapLabel.className = 'inspector-label'
  overlapLabel.textContent = `Overlaps · ${overlaps.length}`
  overlapSection.append(overlapLabel, ...overlaps.slice(0, 12).map(inspectorNodeButton))
  inspector.appendChild(overlapSection)
}

function inspectorSection(labelText: string, valueText: string): HTMLElement {
  const section = document.createElement('section')
  section.className = 'inspector-section'
  const label = document.createElement('span')
  label.className = 'inspector-label'
  label.textContent = labelText
  const value = document.createElement('p')
  value.className = 'inspector-value'
  value.textContent = valueText
  section.append(label, value)
  return section
}

function inspectorNodeButton(node: VizNode): HTMLButtonElement {
  const button = document.createElement('button')
  button.className = 'inspector-node'
  button.type = 'button'
  const dot = document.createElement('span')
  dot.className = 'layer-dot'
  setLayerColor(dot, node.layer)
  const label = document.createElement('span')
  label.textContent = `${node.layer} · ${nodeLabel(node)}`
  button.append(dot, label)
  button.addEventListener('click', () => setSelection({ type: 'node', id: node.id }))
  return button
}

function svgElement<K extends keyof SVGElementTagNameMap>(name: K): SVGElementTagNameMap[K] {
  return document.createElementNS('http://www.w3.org/2000/svg', name)
}

function truncate(value: string, maxLength: number): string {
  return value.length <= maxLength ? value : `${value.slice(0, Math.max(1, maxLength - 1))}…`
}
