import { describe, expect, it } from 'vitest'
import type { AlfredEvent } from '../../../api/events'
import { applyActivityEvent } from './activity'

const tool = (session: string, label: string): AlfredEvent => ({
  type: 'agent_progress',
  session,
  kind: 'tool',
  content: 'X',
  label,
  ts: 1,
})

describe('applyActivityEvent', () => {
  it('lists what Alfred himself is doing', () => {
    expect(applyActivityEvent([], tool('alfred', 'Pesquisando na web'))).toEqual([
      { id: 1, text: 'Pesquisando na web' },
    ])
  })

  it('ignores delegated sessions and their replies', () => {
    const items = [{ id: 1, text: 'Pesquisando na web' }]
    const reply: AlfredEvent = {
      type: 'alfred_reply',
      session: 'back',
      text: 'x',
      summary: 'x',
      ts: 1,
    }

    expect(applyActivityEvent(items, tool('back', 'Executando um comando'))).toBe(items)
    expect(applyActivityEvent(items, reply)).toBe(items)
  })

  it("clears on Alfred's reply", () => {
    const reply: AlfredEvent = {
      type: 'alfred_reply',
      session: 'alfred',
      text: 'x',
      summary: 'x',
      ts: 1,
    }

    expect(applyActivityEvent([{ id: 1, text: 'a' }], reply)).toEqual([])
  })
})
