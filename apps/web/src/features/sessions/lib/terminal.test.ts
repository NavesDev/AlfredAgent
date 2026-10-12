import { describe, expect, it } from 'vitest'
import type { AlfredEvent } from '../../../api/events'
import { applyTerminalEvent, TERMINAL_LINES } from './terminal'

const tool = (session: string, content: string, detail: string | null = null): AlfredEvent => ({
  type: 'agent_progress',
  session,
  kind: 'tool',
  content,
  detail,
  ts: 1,
})

describe('applyTerminalEvent', () => {
  it('keeps the last tool calls of each session as terminal lines', () => {
    let lines = applyTerminalEvent({}, tool('back', 'Edit', 'billing.py'))
    lines = applyTerminalEvent(lines, tool('back', 'Bash', 'Roda os testes'))
    lines = applyTerminalEvent(lines, tool('front', 'Read'))

    expect(lines).toEqual({
      back: ['› Edit billing.py', '› Bash Roda os testes'],
      front: ['› Read'],
    })
  })

  it('drops the oldest line past the limit', () => {
    let lines = {}
    for (let i = 0; i < TERMINAL_LINES + 2; i++)
      lines = applyTerminalEvent(lines, tool('back', `T${i}`))

    expect(lines).toEqual({
      back: Array.from({ length: TERMINAL_LINES }, (_, i) => `› T${i + 2}`),
    })
  })

  it('ignores text, Alfred himself and other events, and forgets deleted sessions', () => {
    const lines = { back: ['› Read'] }
    const text: AlfredEvent = {
      type: 'agent_progress',
      session: 'back',
      kind: 'text',
      content: 'oi',
      ts: 1,
    }

    expect(applyTerminalEvent(lines, text)).toBe(lines)
    expect(applyTerminalEvent(lines, tool('alfred', 'WebSearch'))).toBe(lines)
    expect(applyTerminalEvent(lines, { type: 'session_deleted', name: 'back', ts: 1 })).toEqual({})
  })
})
