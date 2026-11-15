import { describe, expect, it } from 'vitest'
import { SECTIONS, sectionFromHash } from './sections'

describe('sectionFromHash', () => {
  it('opens the section named in the link, usage by default', () => {
    expect(sectionFromHash('#mcps')).toBe('mcps')
    expect(sectionFromHash('#modelos')).toBe('modelos')
    expect(sectionFromHash('')).toBe('uso')
    expect(sectionFromHash('#painel')).toBe('uso')
    expect(sectionFromHash('#atualizacoes')).toBe('atualizacoes')
  })

  it('lists the sections in the sidebar order', () => {
    expect(SECTIONS.map((s) => s.label)).toEqual([
      'Uso e limites',
      'Modelos',
      'Sessões abertas',
      'MCPs',
      'Atualizações',
    ])
  })
})
