import { describe, expect, it } from 'vitest'
import type { AlfredEvent, SessionView } from '../../../api/events'
import { applySessionEvent } from './sessions'

const view = (name: string, over: Partial<SessionView> = {}): SessionView => ({
  name,
  kind: 'geral',
  label: 'Geral',
  model: 'sonnet',
  cwd: '~',
  status: 'idle',
  task: null,
  activity: null,
  queue: 0,
  tasks_done: 0,
  tokens: 0,
  last_summary: null,
  protected: false,
  ...over,
})

describe('applySessionEvent', () => {
  it('appends a created session and replaces it on status', () => {
    let list = applySessionEvent([], { type: 'session_created', session: view('sistema'), ts: 1 })
    list = applySessionEvent(list, {
      type: 'session_status',
      session: view('sistema', { status: 'busy', task: 'gira' }),
      ts: 2,
    })

    expect(list).toEqual([view('sistema', { status: 'busy', task: 'gira' })])
  })

  it('keeps order and adds a status for an unknown session at the end', () => {
    const list = applySessionEvent([view('a'), view('b')], {
      type: 'session_cleared',
      session: view('a', { tokens: 0 }),
      ts: 1,
    })
    const more = applySessionEvent(list, { type: 'session_status', session: view('c'), ts: 2 })

    expect(more.map((s) => s.name)).toEqual(['a', 'b', 'c'])
  })

  it('removes a deleted session', () => {
    const list = applySessionEvent([view('a'), view('b')], {
      type: 'session_deleted',
      name: 'a',
      ts: 1,
    })

    expect(list.map((s) => s.name)).toEqual(['b'])
  })

  it('returns the same list for other events', () => {
    const list = [view('a')]
    const other: AlfredEvent = { type: 'voice_state', state: 'idle', ts: 1 }

    expect(applySessionEvent(list, other)).toBe(list)
  })
})
