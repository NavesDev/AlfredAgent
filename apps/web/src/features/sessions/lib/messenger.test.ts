import { describe, expect, it } from 'vitest'
import { sessionView } from '../../../lib/sessionView'
import { FLASH_MS } from './butler'
import { messengerState } from './messenger'

describe('messengerState', () => {
  it('naps when idle and carries the tray while busy', () => {
    expect(messengerState(sessionView('notes'), null, 0)).toBe('sleeping')
    expect(messengerState(sessionView('notes', { status: 'busy' }), null, 0)).toBe('carrying')
  })

  it('checks the watch while waiting for a free slot, even after an error', () => {
    expect(messengerState(sessionView('notes', { waiting: true }), null, 0)).toBe('queued')
    expect(messengerState(sessionView('notes', { status: 'error', waiting: true }), null, 0)).toBe(
      'queued',
    )
  })

  it('shows the error face', () => {
    expect(messengerState(sessionView('notes', { status: 'error' }), null, 0)).toBe('error')
  })

  it('salutes for a while after a task ends, ignoring subagent letters', () => {
    const idle = sessionView('notes')
    expect(messengerState(idle, { state: 'done', at: 100 }, 100)).toBe('done')
    expect(messengerState(idle, { state: 'done', at: 100 }, 100 + FLASH_MS.done)).toBe('sleeping')
    expect(messengerState(idle, { state: 'delegating', at: 100 }, 100)).toBe('sleeping')
  })
})
