import { describe, expect, it } from 'vitest'
import { sessionView } from './sessionView'
import { contextLevel, gradientFor, initials, presence } from './presence'

describe('presence', () => {
  it('names what the session is doing, errors first', () => {
    expect(presence(sessionView('a', { status: 'error', waiting: true }))).toEqual({
      label: 'Erro',
      tone: 'error',
    })
    expect(presence(sessionView('a', { status: 'busy' }))).toEqual({
      label: 'Trabalhando',
      tone: 'work',
    })
    expect(presence(sessionView('a', { waiting: true }))).toEqual({
      label: 'Na fila',
      tone: 'queue',
    })
    expect(presence(sessionView('a', { connected: true }))).toEqual({
      label: 'Livre',
      tone: 'idle',
    })
    expect(presence(sessionView('a'))).toEqual({ label: 'Dormindo', tone: 'sleep' })
  })
})

describe('monogram', () => {
  it('takes the first letter of up to two words', () => {
    expect(initials('Site Sales')).toBe('SS')
    expect(initials('developer')).toBe('D')
    expect(initials('  meu  app de vendas ')).toBe('MA')
  })

  it('gives the same name the same gradient', () => {
    expect(gradientFor('Design')).toEqual(gradientFor('Design'))
    expect(gradientFor('Design')).toHaveLength(2)
  })
})

describe('contextLevel', () => {
  it('is unknown before the first task', () => {
    expect(contextLevel(null, 200_000)).toBeNull()
    expect(contextLevel(10, null)).toBeNull()
  })

  it('warms up at 60% and turns hot at 80%', () => {
    expect(contextLevel(84_000, 200_000)).toEqual({ share: 42, tone: 'ok' })
    expect(contextLevel(130_000, 200_000)).toEqual({ share: 65, tone: 'warm' })
    expect(contextLevel(190_000, 200_000)).toEqual({ share: 95, tone: 'hot' })
    expect(contextLevel(300_000, 200_000)).toEqual({ share: 100, tone: 'hot' })
  })
})
