import { describe, expect, it } from 'vitest'
import type { ResultView } from '../../../api/events'
import {
  cleanMarkdown,
  fileUrl,
  formatSize,
  isLocalHost,
  mainAction,
  shownChanges,
  timeLabel,
  totals,
} from './results'

const result = (over: Partial<ResultView> = {}): ResultView => ({
  id: 7,
  session: 'Design',
  source: 'session',
  title: 'Retrato pronto',
  summary: null,
  report: null,
  changes: [],
  files: [],
  created_at: 0,
  ...over,
})

describe('results lib', () => {
  it('serves a file by result id and index', () => {
    expect(fileUrl(7, 2)).toBe('/api/results/7/files/2')
  })

  it('knows this computer by its hostname only', () => {
    for (const host of ['localhost', '127.0.0.1', '[::1]', '::1'])
      expect(isLocalHost(host)).toBe(true)
    for (const host of ['192.168.0.20', 'alfred.local', '']) expect(isLocalHost(host)).toBe(false)
  })

  it('shows up to three changed files and counts the rest', () => {
    const changes = ['a', 'b', 'c', 'd', 'e'].map((path) => ({ path, added: 1, removed: 2 }))
    expect(shownChanges(changes)).toEqual({ shown: changes.slice(0, 3), more: 2 })
    expect(totals(changes)).toEqual({ added: 5, removed: 10 })
  })

  it('formats sizes the Brazilian way', () => {
    expect(formatSize(900)).toBe('900 B')
    expect(formatSize(12_300)).toBe('12 KB')
    expect(formatSize(4_200_000)).toBe('4,2 MB')
  })

  it('opens what cannot be previewed and expands the rest', () => {
    const file = { name: 'x', size: 1, exists: true }
    expect(mainAction({ ...file, kind: 'other' })).toBe('open')
    expect(mainAction({ ...file, kind: 'image' })).toBe('expand')
    expect(mainAction({ ...file, kind: 'text', size: 2_000_000 })).toBe('open')
    expect(mainAction({ ...file, kind: 'image', exists: false })).toBe('none')
    expect(result().files).toEqual([])
  })
})

describe('timeLabel', () => {
  const now = new Date(2026, 10, 15, 15, 0)
  it('says the hour today, ontem, else the date', () => {
    expect(timeLabel(new Date(2026, 10, 15, 14, 32).getTime() / 1000, now)).toBe('14:32')
    expect(timeLabel(new Date(2026, 10, 14, 9, 0).getTime() / 1000, now)).toBe('ontem')
    expect(timeLabel(new Date(2026, 10, 12, 9, 0).getTime() / 1000, now)).toBe('12/11')
  })
})

describe('cleanMarkdown', () => {
  it('drops the front matter', () => {
    expect(cleanMarkdown('---\ntipo: spec\nversao: 1\n---\n# Spec\n')).toBe('# Spec\n')
  })

  it('keeps a horizontal rule that is not front matter', () => {
    expect(cleanMarkdown('# A\n\n---\n\nB')).toBe('# A\n\n---\n\nB')
  })

  it('turns wiki links into their alias or note name', () => {
    expect(cleanMarkdown('ver [[30-Projetos/X/PRD|PRD]] e [[Índice]] e [[a/b#Seção]]')).toBe(
      'ver PRD e Índice e b',
    )
  })
  it('gives a callout a bold title', () => {
    expect(cleanMarkdown('> [!warning] Bloqueios\n> - a\n\n> [!NOTE]\n> b')).toBe(
      '> **Bloqueios**\n> - a\n\n> **Note**\n> b',
    )
  })
})
