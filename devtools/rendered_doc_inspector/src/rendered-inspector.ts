import inspectorData from '../generated/inspector-data.json'

import {
  buildLayerForest,
  normalizeThemeMode,
  resolveHoverTrail,
  resolveThemeMode,
  scrollTopToReveal,
  spansContain,
  splitSourceForSpan,
  type InspectorNode,
  type InspectorTreeNode,
  type SourceSpan,
  type ThemeMode,
} from './inspector-model'

interface InspectorPayload {
  schema: string
  layerNesting: Record<string, 'ordered_list' | 'tree'>
  source: {
    filename: string
    offsetUnit: string
    text: string
  }
  nodes: InspectorNode[]
  rendered_html: string
}

type InspectorView = 'markdown' | 'tree' | null

/** Duration of visible confirmation after a copy action. */
const COPY_FEEDBACK_DURATION_MS = 1600

/** Additional outward spacing between nested ancestor outlines. */
const CONTAINER_OUTLINE_LEVEL_STEP_REM = 0.125

/** Maximum code-point length of secondary structure labels. */
const MAX_TRAIL_LABEL_CODE_POINTS = 46

/** Limit visual expansion for unusually deep rendered structures. */
const MAX_CONTAINER_OUTLINE_LEVEL = 4

const SYSTEM_THEME_QUERY = '(prefers-color-scheme: dark)'
const THEME_STORAGE_KEY = 'flexdoc.inspector.theme'
const TREE_LAYERS = ['document', 'markdown', 'textual'] as const

const data = inspectorData as InspectorPayload

const activeSpan = requiredElement<HTMLElement>('active-span')
const copyRenderedButton = requiredElement<HTMLButtonElement>('copy-rendered')
const copySourceButton = requiredElement<HTMLButtonElement>('copy-source')
const copyStatus = requiredElement<HTMLElement>('copy-status')
const documentFilename = requiredElement<HTMLElement>('document-filename')
const graphSchema = requiredElement<HTMLElement>('graph-schema')
const hoverHint = requiredElement<HTMLElement>('hover-hint')
const inspectorPane = requiredElement<HTMLElement>('inspector-pane')
const renderedDocument = requiredElement<HTMLElement>('rendered-document')
const sourceActive = requiredElement<HTMLElement>('source-active')
const sourceAfter = requiredElement<HTMLElement>('source-after')
const sourceBefore = requiredElement<HTMLElement>('source-before')
const sourceCode = requiredElement<HTMLElement>('source-code')
const sourceView = requiredElement<HTMLElement>('source-view')
const structureTrail = requiredElement<HTMLElement>('structure-trail')
const themeSettings = requiredElement<HTMLElement>('theme-settings')
const themeSettingsButton = requiredElement<HTMLButtonElement>('theme-settings-button')
const toggleSourceButton = requiredElement<HTMLButtonElement>('toggle-source')
const toggleTreeButton = requiredElement<HTMLButtonElement>('toggle-tree')
const treeRoot = requiredElement<HTMLElement>('tree-root')
const treeScroll = requiredElement<HTMLElement>('tree-scroll')
const treeView = requiredElement<HTMLElement>('tree-view')
const workspace = requiredElement<HTMLElement>('workspace')
const themeChoiceButtons = [
  ...document.querySelectorAll<HTMLButtonElement>('[data-kpress-theme-choice]'),
]
const systemThemeQuery = window.matchMedia(SYSTEM_THEME_QUERY)

let currentSpan: SourceSpan | null = null
let currentDirectNodeId: string | null = null
let currentInspectorView: InspectorView = null
let currentTrail: InspectorNode[] = []
let currentTheme: ThemeMode = normalizeThemeMode(document.documentElement.dataset['kpressTheme'])
const treeRowsById = new Map<string, HTMLElement>()

renderedDocument.innerHTML = data.rendered_html
documentFilename.textContent = data.source.filename
graphSchema.textContent = data.schema
sourceBefore.textContent = data.source.text
renderDocGraphTree()
initializeTheme()

const mappedElements = [...renderedDocument.querySelectorAll<HTMLElement>('[data-source-span]')]
for (const element of mappedElements) {
  if (!isNativelyFocusable(element)) element.tabIndex = 0
}

renderedDocument.addEventListener('pointerover', event => {
  const target = event.target instanceof Element ? event.target.closest<HTMLElement>('[data-source-span]') : null
  if (target !== null && renderedDocument.contains(target)) activateElement(target)
})

renderedDocument.addEventListener('focusin', event => {
  const target = event.target instanceof Element ? event.target.closest<HTMLElement>('[data-source-span]') : null
  if (target !== null) activateElement(target)
})

toggleSourceButton.addEventListener('click', () => {
  toggleInspectorView('markdown')
})

toggleTreeButton.addEventListener('click', () => {
  toggleInspectorView('tree')
})

copyRenderedButton.addEventListener('click', () => {
  void copyText(
    renderedDocument.innerText,
    renderedDocument,
    'Rendered text copied',
    'Rendered text selected; press Command-C or Ctrl-C to copy',
  ).catch(showCopyFailure)
})
copySourceButton.addEventListener('click', () => {
  void copyText(
    data.source.text,
    sourceCode,
    'Markdown copied',
    'Markdown selected; press Command-C or Ctrl-C to copy',
  ).catch(showCopyFailure)
})

themeSettingsButton.addEventListener('click', () => {
  setThemeMenuOpen(themeSettings.getAttribute('aria-expanded') !== 'true')
})

for (const button of themeChoiceButtons) {
  button.addEventListener('click', () => {
    applyTheme(normalizeThemeMode(button.dataset['kpressThemeChoice']), true)
  })
}

document.addEventListener('pointerdown', event => {
  if (event.target instanceof Node && !themeSettings.contains(event.target)) {
    setThemeMenuOpen(false)
  }
})

document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && themeSettings.getAttribute('aria-expanded') === 'true') {
    setThemeMenuOpen(false)
    themeSettingsButton.focus()
  }
})

systemThemeQuery.addEventListener('change', () => {
  if (currentTheme === 'system') applyTheme('system', false)
})

function toggleInspectorView(view: Exclude<InspectorView, null>): void {
  setInspectorView(currentInspectorView === view ? null : view)
}

function setInspectorView(view: InspectorView): void {
  currentInspectorView = view
  const markdownVisible = view === 'markdown'
  const treeVisible = view === 'tree'
  inspectorPane.hidden = view === null
  sourceView.hidden = !markdownVisible
  treeView.hidden = !treeVisible
  workspace.classList.toggle('inspector-visible', view !== null)
  toggleSourceButton.setAttribute('aria-pressed', String(markdownVisible))
  toggleTreeButton.setAttribute('aria-pressed', String(treeVisible))

  if (markdownVisible && currentSpan !== null) {
    scrollElementWithinContainer(sourceCode, sourceActive)
  }
  if (treeVisible) renderTreeSelection(currentTrail, currentDirectNodeId)
}

function activateElement(element: HTMLElement): void {
  const span = parseSpan(element.dataset['sourceSpan'])
  if (span === null) return
  currentSpan = span
  currentDirectNodeId = element.dataset['nodeId'] ?? null
  currentTrail = resolveHoverTrail(data.nodes, span, currentDirectNodeId)
  const containers: HTMLElement[] = []

  for (const candidate of mappedElements) {
    const candidateSpan = parseSpan(candidate.dataset['sourceSpan'])
    const isDirect = candidate === element
    const isContainer = candidateSpan !== null && spansContain(candidateSpan, span) && !isDirect
    candidate.classList.toggle('is-hovered', isDirect)
    candidate.classList.toggle('is-container', isContainer)
    if (isContainer) {
      containers.push(candidate)
    } else {
      candidate.style.removeProperty('--inspector-container-level-gap')
    }
  }

  for (const container of containers) {
    const containedContainers = containers.filter(
      candidate => candidate !== container && container.contains(candidate),
    ).length
    const level = Math.min(containedContainers, MAX_CONTAINER_OUTLINE_LEVEL)
    container.style.setProperty(
      '--inspector-container-level-gap',
      `${level * CONTAINER_OUTLINE_LEVEL_STEP_REM}rem`,
    )
  }

  renderTrail(currentTrail)
  renderSourceSelection(span)
  renderTreeSelection(currentTrail, currentDirectNodeId)
}

function renderTrail(trail: readonly InspectorNode[]): void {
  structureTrail.replaceChildren()
  for (const [index, node] of trail.entries()) {
    if (index > 0) {
      const separator = document.createElement('span')
      separator.className = 'trail-separator'
      separator.textContent = '›'
      separator.setAttribute('aria-hidden', 'true')
      structureTrail.appendChild(separator)
    }
    const item = document.createElement('span')
    item.className = 'trail-node'
    item.dataset['layer'] = node.layer
    const layer = document.createElement('span')
    layer.className = 'trail-layer'
    layer.textContent = node.layer
    const label = document.createElement('span')
    label.className = 'trail-label'
    label.textContent = nodeLabel(node)
    item.append(layer, label)
    structureTrail.appendChild(item)
  }
  hoverHint.hidden = true
  structureTrail.hidden = false
  activeSpan.hidden = currentSpan === null
  activeSpan.textContent = currentSpan === null ? '' : `${currentSpan.start}:${currentSpan.end}`
}

function renderDocGraphTree(): void {
  treeRoot.replaceChildren()
  treeRowsById.clear()
  for (const layer of TREE_LAYERS) {
    const forest = buildLayerForest(data.nodes, layer)
    const section = document.createElement('section')
    section.className = 'tree-layer-section'
    section.dataset['layer'] = layer

    const heading = document.createElement('h3')
    heading.className = 'tree-layer-heading'
    const marker = document.createElement('span')
    marker.className = 'tree-layer-marker'
    marker.setAttribute('aria-hidden', 'true')
    const name = document.createElement('span')
    name.textContent = `${layer.charAt(0).toUpperCase()}${layer.slice(1)}`
    const count = document.createElement('span')
    count.className = 'tree-layer-count'
    const nesting = data.layerNesting[layer]
    if (nesting === undefined) {
      throw new Error(`Inspector payload does not declare nesting for ${layer}.`)
    }
    const nestingLabel = nesting.replaceAll('_', ' ')
    count.textContent = `${nestingLabel}, ${data.nodes.filter(node => node.layer === layer).length} nodes`
    heading.append(marker, name, count)

    const list = document.createElement('ul')
    list.className = 'tree-list tree-list-root'
    list.setAttribute('aria-label', `${name.textContent} layer`)
    list.append(...forest.map(renderTreeBranch))
    section.append(heading, list)
    treeRoot.appendChild(section)
  }
}

function renderTreeBranch(branch: InspectorTreeNode): HTMLLIElement {
  const item = document.createElement('li')

  const row = document.createElement('div')
  row.className = 'tree-node-row'
  row.dataset['nodeId'] = branch.node.id
  row.dataset['layer'] = branch.node.layer
  const label = document.createElement('span')
  label.className = 'tree-node-label'
  label.textContent = nodeLabel(branch.node)
  const meta = document.createElement('code')
  meta.className = 'tree-node-meta'
  meta.textContent = branch.node.sourceSpan === null
    ? `${branch.node.id} [unlocated]`
    : `${branch.node.id} [${branch.node.sourceSpan.start}:${branch.node.sourceSpan.end}]`
  row.append(label, meta)
  treeRowsById.set(branch.node.id, row)
  item.appendChild(row)

  if (branch.children.length > 0) {
    const children = document.createElement('ul')
    children.className = 'tree-list'
    children.append(...branch.children.map(renderTreeBranch))
    item.appendChild(children)
  }
  return item
}

function renderTreeSelection(
  trail: readonly InspectorNode[],
  directNodeId: string | null,
): void {
  const trailIds = new Set(trail.map(node => node.id))
  for (const [nodeId, row] of treeRowsById) {
    row.classList.toggle('is-tree-path', trailIds.has(nodeId))
    row.classList.toggle('is-tree-direct', nodeId === directNodeId)
  }
  if (currentInspectorView !== 'tree') return

  let target = directNodeId === null ? undefined : treeRowsById.get(directNodeId)
  for (let index = trail.length - 1; target === undefined && index >= 0; index -= 1) {
    target = treeRowsById.get(trail[index]?.id ?? '')
  }
  if (target !== undefined) scrollElementWithinContainer(treeScroll, target)
}

function renderSourceSelection(span: SourceSpan): void {
  const split = splitSourceForSpan(data.source.text, span)
  sourceBefore.textContent = split.before
  sourceActive.textContent = split.active
  sourceAfter.textContent = split.after
  if (currentInspectorView === 'markdown') {
    scrollElementWithinContainer(sourceCode, sourceActive)
  }
}

function scrollElementWithinContainer(scroller: HTMLElement, target: HTMLElement): void {
  requestAnimationFrame(() => {
    const scrollerBounds = scroller.getBoundingClientRect()
    const targetBounds = target.getBoundingClientRect()
    const currentScrollTop = scroller.scrollTop
    const nextScrollTop = scrollTopToReveal({
      contentHeight: scroller.scrollHeight,
      currentScrollTop,
      targetHeight: targetBounds.height,
      targetTop: targetBounds.top - scrollerBounds.top + currentScrollTop,
      viewportHeight: scroller.clientHeight,
    })
    if (nextScrollTop !== currentScrollTop) scroller.scrollTop = nextScrollTop
  })
}

function nodeLabel(node: InspectorNode): string {
  const detail = node.attrs['title']
    ?? node.attrs['text']
    ?? node.attrs['content']
    ?? node.text
  const kind = node.kind.replaceAll('_', ' ')
  if (typeof detail !== 'string' || detail.length === 0) return kind
  const normalizedDetail = detail.replaceAll(/\s+/g, ' ').trim()
  const codePoints = Array.from(normalizedDetail)
  const shortened = codePoints.length > MAX_TRAIL_LABEL_CODE_POINTS
    ? `${codePoints.slice(0, MAX_TRAIL_LABEL_CODE_POINTS).join('')}…`
    : normalizedDetail
  return `${kind}: ${shortened}`
}

function parseSpan(value: string | undefined): SourceSpan | null {
  if (value === undefined) return null
  const [startText, endText, ...extra] = value.split(':')
  if (startText === undefined || endText === undefined || extra.length > 0) return null
  const start = Number(startText)
  const end = Number(endText)
  if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end < start) return null
  return { start, end }
}

function initializeTheme(): void {
  let storedTheme: string | null = null
  try {
    storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY)
  } catch {
    storedTheme = null
  }
  applyTheme(normalizeThemeMode(storedTheme ?? currentTheme), false)
}

function applyTheme(mode: ThemeMode, persist: boolean): void {
  currentTheme = mode
  const resolved = resolveThemeMode(mode, systemThemeQuery.matches)
  document.documentElement.dataset['kpressTheme'] = mode
  document.documentElement.dataset['kpressResolvedTheme'] = resolved
  for (const button of themeChoiceButtons) {
    button.setAttribute(
      'aria-checked',
      String(button.dataset['kpressThemeChoice'] === mode),
    )
  }
  if (!persist) return
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, mode)
  } catch {
    showTransientStatus('Theme changed for this tab, but the preference could not be saved.')
  }
}

function setThemeMenuOpen(open: boolean): void {
  themeSettings.setAttribute('aria-expanded', String(open))
  themeSettingsButton.setAttribute('aria-expanded', String(open))
}

function isNativelyFocusable(element: HTMLElement): boolean {
  return element.matches('a[href], button, input, select, textarea')
}

async function copyText(
  text: string,
  selectionTarget: HTMLElement,
  confirmation: string,
  fallbackConfirmation: string,
): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
    showTransientStatus(confirmation)
  } catch {
    selectElementContents(selectionTarget)
    showTransientStatus(fallbackConfirmation)
  }
}

function selectElementContents(element: HTMLElement): void {
  const selection = window.getSelection()
  if (selection === null) throw new Error('This browser does not expose text selection.')
  const range = document.createRange()
  range.selectNodeContents(element)
  selection.removeAllRanges()
  selection.addRange(range)
}

function showTransientStatus(message: string): void {
  copyStatus.textContent = message
  copyStatus.classList.add('is-visible')
  window.setTimeout(() => copyStatus.classList.remove('is-visible'), COPY_FEEDBACK_DURATION_MS)
}

function showCopyFailure(error: unknown): void {
  showTransientStatus(error instanceof Error ? error.message : 'Copy failed.')
}

function requiredElement<T extends HTMLElement>(id: string): T {
  const element = document.getElementById(id)
  if (element === null) throw new Error(`Missing required inspector element: #${id}`)
  return element as T
}
