import { describe, expect, it } from 'vitest'
import { sessionView } from '../../../lib/sessionView'
import { lineOf, lookOf } from './look'

describe('lookOf', () => {
  it('draws the butler for implementation sessions and the messenger for the rest', () => {
    const code = sessionView('back', { kind: 'implementacao' })
    const general = sessionView('notes', { kind: 'geral' })
    expect(lookOf(code, null, 0)).toEqual({ figure: 'butler', state: 'sleeping' })
    expect(lookOf(general, null, 0)).toEqual({ figure: 'messenger', state: 'sleeping' })
  })
})

describe('lineOf', () => {
  it('adds the activity while busy', () => {
    const busy = sessionView('notes', { kind: 'geral', status: 'busy', activity: 'lendo docs' })
    expect(lineOf(lookOf(busy, null, 0), busy)).toBe('trabalhando · lendo docs')
  })

  it('says only the state otherwise', () => {
    const queued = sessionView('notes', { kind: 'geral', waiting: true })
    expect(lineOf(lookOf(queued, null, 0), queued)).toBe('na fila por uma vaga')
  })
})
