import inspectorData from '../generated/inspector-data.json'

import {
  resolveHoverTrail,
  spansContain,
  splitSourceForSpan,
  type InspectorNode,
  type SourceSpan,
} from './inspector-model'

interface InspectorPayload {
  source: {
    filename: string
    offsetUnit: string
    text: string
  }
  nodes: InspectorNode[]
  rendered_html: string
}

/** Duration of visible confirmation after a copy action. */
const COPY_FEEDBACK_DURATION_MS = 1600

/** Maximum code-point length of secondary structure labels. */
const MAX_TRAIL_LABEL_CODE_POINTS = 46

const data = inspectorData as InspectorPayload

const activeSpan = requiredElement<HTMLElement>('active-span')
const copyRenderedButton = requiredElement<HTMLButtonElement>('copy-rendered')
const copySourceButton = requiredElement<HTMLButtonElement>('copy-source')
const copyStatus = requiredElement<HTMLElement>('copy-status')
const documentFilename = requiredElement<HTMLElement>('document-filename')
const hoverHint = requiredElement<HTMLElement>('hover-hint')
const renderedDocument = requiredElement<HTMLElement>('rendered-document')
const sourceActive = requiredElement<HTMLElement>('source-active')
const sourceAfter = requiredElement<HTMLElement>('source-after')
const sourceBefore = requiredElement<HTMLElement>('source-before')
const sourceCode = requiredElement<HTMLElement>('source-code')
const sourcePane = requiredElement<HTMLElement>('source-pane')
const structureTrail = requiredElement<HTMLElement>('structure-trail')
const toggleSourceButton = requiredElement<HTMLButtonElement>('toggle-source')
const workspace = requiredElement<HTMLElement>('workspace')

let currentSpan: SourceSpan | null = null

renderedDocument.innerHTML = data.rendered_html
documentFilename.textContent = data.source.filename
sourceBefore.textContent = data.source.text

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
  const showSource = toggleSourceButton.getAttribute('aria-pressed') !== 'true'
  toggleSourceButton.setAttribute('aria-pressed', String(showSource))
  toggleSourceButton.textContent = showSource ? 'Hide Markdown' : 'Show Markdown'
  sourcePane.hidden = !showSource
  workspace.classList.toggle('source-visible', showSource)
  if (showSource && currentSpan !== null) scrollSourceSelectionIntoView()
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

function activateElement(element: HTMLElement): void {
  const span = parseSpan(element.dataset['sourceSpan'])
  if (span === null) return
  currentSpan = span
  const directNodeId = element.dataset['nodeId'] ?? null
  const trail = resolveHoverTrail(data.nodes, span, directNodeId)

  for (const candidate of mappedElements) {
    const candidateSpan = parseSpan(candidate.dataset['sourceSpan'])
    const isDirect = candidate === element
    const isContainer = candidateSpan !== null && spansContain(candidateSpan, span) && !isDirect
    candidate.classList.toggle('is-hovered', isDirect)
    candidate.classList.toggle('is-container', isContainer)
  }

  renderTrail(trail)
  renderSourceSelection(span)
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

function renderSourceSelection(span: SourceSpan): void {
  const split = splitSourceForSpan(data.source.text, span)
  sourceBefore.textContent = split.before
  sourceActive.textContent = split.active
  sourceAfter.textContent = split.after
  if (!sourcePane.hidden) scrollSourceSelectionIntoView()
}

function scrollSourceSelectionIntoView(): void {
  requestAnimationFrame(() => sourceActive.scrollIntoView({ block: 'center', inline: 'nearest' }))
}

function nodeLabel(node: InspectorNode): string {
  const detail = node.attrs['title'] ?? node.attrs['text'] ?? node.attrs['content']
  const kind = node.kind.replaceAll('_', ' ')
  if (typeof detail !== 'string' || detail.length === 0) return kind
  const codePoints = Array.from(detail)
  const shortened = codePoints.length > MAX_TRAIL_LABEL_CODE_POINTS
    ? `${codePoints.slice(0, MAX_TRAIL_LABEL_CODE_POINTS).join('')}…`
    : detail
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
    showCopyStatus(confirmation)
  } catch {
    selectElementContents(selectionTarget)
    showCopyStatus(fallbackConfirmation)
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

function showCopyStatus(message: string): void {
  copyStatus.textContent = message
  copyStatus.classList.add('is-visible')
  window.setTimeout(() => copyStatus.classList.remove('is-visible'), COPY_FEEDBACK_DURATION_MS)
}

function showCopyFailure(error: unknown): void {
  showCopyStatus(error instanceof Error ? error.message : 'Copy failed.')
}

function requiredElement<T extends HTMLElement>(id: string): T {
  const element = document.getElementById(id)
  if (element === null) throw new Error(`Missing required inspector element: #${id}`)
  return element as T
}
