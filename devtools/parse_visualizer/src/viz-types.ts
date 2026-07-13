export type LayerName = 'document' | 'markdown' | 'textual'

export type SourceSpan = {
  start: number
  end: number
}

export type VizNode = {
  id: string
  kind: string
  layer: LayerName
  parent: string | null
  children: string[]
  source_span: SourceSpan | null
  utf16_span?: SourceSpan
  attrs: Record<string, unknown>
  text: string | null
}

export type VizWordtok = {
  id: string
  value: string
  exact: string
  kind: 'entity' | 'number' | 'punctuation' | 'tag' | 'whitespace' | 'word'
  source_span: SourceSpan
  utf16_span: SourceSpan
}

export type VizData = {
  schema: string
  title: string
  source: {
    format: string
    offset_unit: 'unicode_code_points'
    sha256: string
    text: string
  }
  nodes: VizNode[]
  roots: string[]
  views: {
    toc: string[]
    blocks: string[]
    links: string[]
    paragraphs: string[]
    sentences: string[]
  }
  wordtoks: VizWordtok[]
  line_starts: number[]
}

export type VizSelection =
  | { type: 'node'; id: string }
  | { type: 'wordtok'; id: string }

export type VizMode =
  | 'flow'
  | 'graph'
  | 'hierarchy'
  | 'microscope'
  | 'pretext'
  | 'source'
  | 'tracks'
