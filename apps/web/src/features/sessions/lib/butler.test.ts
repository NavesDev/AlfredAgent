import { describe, expect, it } from 'vitest'
import type { AlfredEvent } from '../../../api/events'
import { sessionView } from '../../../lib/sessionView'
import { baseState, butlerState, flashFor, FLASH_MS } from './butler'

const busy = (phase: 'exploring' | 'editing' | 'running' | null) =>
  sessionView('back', { status: 'busy', phase })

describe('baseState', () => {
  it('naps when idle, with or without a process', () => {
    expect(baseState(sessionView('back'))).toBe('sleeping')
    expect(baseState(sessionView('back', { connected: true }))).toBe('sleeping')
  })

  it('follows the phase while busy, typing when it is unknown', () => {
    expect(baseState(busy('exploring'))).toBe('exploring')
    expect(baseState(busy('editing'))).toBe('editing')
    expect(baseState(busy('running'))).toBe('running')
    expect(baseState(busy(null))).toBe('editing')
  })

  it('shows the error face', () => {
    expect(baseState(sessionView('back', { status: 'error' }))).toBe('error')
  })
})

describe('flashFor', () => {
  const status = (s: 'idle' | 'busy' | 'error'): AlfredEvent => ({
    type: 'session_status',
    session: sessionView('back', { status: s }),
    ts: 1,
  })

  it('sends a letter when the session calls a subagent', () => {
    const event: AlfredEvent = {
      type: 'subagent_started',
      session: 'back',
      id: 'k1',
      subagent_type: 'Explore',
      description: 'x',
      ts: 1,
    }
    expect(flashFor('back', 'busy', event)).toBe('delegating')
    expect(flashFor('front', 'busy', event)).toBeNull()
  })

  it('does the hat trick only when a task ends well', () => {
    expect(flashFor('back', 'busy', status('idle'))).toBe('done')
    expect(flashFor('back', 'busy', status('error'))).toBeNull()
    expect(flashFor('back', 'idle', status('idle'))).toBeNull()
    expect(flashFor('back', undefined, status('idle'))).toBeNull()
  })
})

describe('butlerState', () => {
  it('plays a flash for its duration, then goes back to the base state', () => {
    const flash = { state: 'done' as const, at: 1000 }
    const idle = sessionView('back')

    expect(butlerState(idle, flash, 1000 + FLASH_MS.done - 1)).toBe('done')
    expect(butlerState(idle, flash, 1000 + FLASH_MS.done)).toBe('sleeping')
    expect(butlerState(idle, null, 0)).toBe('sleeping')
  })

  it('shows an error at once, over any flash', () => {
    const failed = sessionView('back', { status: 'error' })

    expect(butlerState(failed, { state: 'done', at: 0 }, 10)).toBe('error')
    expect(butlerState(failed, { state: 'delegating', at: 0 }, 10)).toBe('error')
  })

  it('keeps the letter short', () => {
    expect(FLASH_MS.delegating).toBeLessThanOrEqual(1600)
    expect(butlerState(busy('editing'), { state: 'delegating', at: 0 }, 100)).toBe('delegating')
  })
})
