import inspectorData from '../generated/inspector-data.json'

import {
  normalizeThemeMode,
  resolveHoverTrail,
  resolveThemeMode,
  scrollTopToReveal,
  spansContain,
  splitSourceForSpan,
  type InspectorNode,
  type SourceSpan,
  type ThemeMode,
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

/** Additional outward spacing between nested ancestor outlines. */
const CONTAINER_OUTLINE_LEVEL_STEP_REM = 0.125

/** Maximum code-point length of secondary structure labels. */
const MAX_TRAIL_LABEL_CODE_POINTS = 46

/** Limit visual expansion for unusually deep rendered structures. */
const MAX_CONTAINER_OUTLINE_LEVEL = 4

const SYSTEM_THEME_QUERY = '(prefers-color-scheme: dark)'
const THEME_STORAGE_KEY = 'flexdoc.inspector.theme'

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
const themeSettings = requiredElement<HTMLElement>('theme-settings')
const themeSettingsButton = requiredElement<HTMLButtonElement>('theme-settings-button')
const toggleSourceButton = requiredElement<HTMLButtonElement>('toggle-source')
const workspace = requiredElement<HTMLElement>('workspace')
const themeChoiceButtons = [
  ...document.querySelectorAll<HTMLButtonElement>('[data-kpress-theme-choice]'),
]
const systemThemeQuery = window.matchMedia(SYSTEM_THEME_QUERY)

let currentSpan: SourceSpan | null = null
let currentTheme: ThemeMode = normalizeThemeMode(document.documentElement.dataset['kpressTheme'])

renderedDocument.innerHTML = data.rendered_html
documentFilename.textContent = data.source.filename
sourceBefore.textContent = data.source.text
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

function activateElement(element: HTMLElement): void {
  const span = parseSpan(element.dataset['sourceSpan'])
  if (span === null) return
  currentSpan = span
  const directNodeId = element.dataset['nodeId'] ?? null
  const trail = resolveHoverTrail(data.nodes, span, directNodeId)
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
  requestAnimationFrame(() => {
    const scrollerBounds = sourceCode.getBoundingClientRect()
    const selectionBounds = sourceActive.getBoundingClientRect()
    const currentScrollTop = sourceCode.scrollTop
    const nextScrollTop = scrollTopToReveal({
      contentHeight: sourceCode.scrollHeight,
      currentScrollTop,
      targetHeight: selectionBounds.height,
      targetTop: selectionBounds.top - scrollerBounds.top + currentScrollTop,
      viewportHeight: sourceCode.clientHeight,
    })
    if (nextScrollTop !== currentScrollTop) sourceCode.scrollTop = nextScrollTop
  })
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
