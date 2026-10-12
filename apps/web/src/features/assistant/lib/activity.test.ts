import { describe, expect, it } from 'vitest'
import type { ActivityAction, AlfredEvent } from '../../../api/events'
import { applyActivityEvent, type Activity } from './activity'

const tool = (
  session: string,
  label: string,
  action?: ActivityAction,
  detail: string | null = null,
  ts = 1,
): AlfredEvent => ({
  type: 'agent_progress',
  session,
  kind: 'tool',
  content: 'X',
  label,
  action,
  detail,
  ts,
})

const reply = (session: string): AlfredEvent => ({
  type: 'alfred_reply',
  session,
  text: 'x',
  summary: 'x',
  ts: 1,
})

const run = (events: AlfredEvent[]) => events.reduce<Activity[]>(applyActivityEvent, [])

describe('applyActivityEvent', () => {
  it('lists what Alfred himself is doing, as a card per kind of step', () => {
    expect(run([tool('alfred', 'Pesquisando na web', 'web_search', 'dólar')])).toEqual([
      { id: 1, action: 'web_search', label: 'Pesquisando na web', detail: 'dólar' },
    ])
  })

  it('falls back to the generic card when the server sends no action', () => {
    expect(run([tool('alfred', 'Usando algo')])[0].action).toBe('tool')
  })

  it('refreshes the last card when the same kind of step repeats', () => {
    const items = run([
      tool('alfred', 'Pesquisando na web', 'web_search', 'dólar', 1),
      tool('alfred', 'Pesquisando na web', 'web_search', 'euro', 2),
    ])
    expect(items).toEqual([
      { id: 1, action: 'web_search', label: 'Pesquisando na web', detail: 'euro' },
    ])
  })

  it('keeps one card more than it shows, so the oldest can slide out', () => {
    const actions: ActivityAction[] = [
      'email_read',
      'web_search',
      'web_page',
      'calendar_read',
      'drive',
    ]
    const items = run(actions.map((a, i) => tool('alfred', a, a, null, i)))
    expect(items.map((i) => i.action)).toEqual(['web_search', 'web_page', 'calendar_read', 'drive'])
  })

  it('ignores delegated sessions and their replies', () => {
    const items = run([tool('alfred', 'Pesquisando na web', 'web_search')])
    expect(applyActivityEvent(items, tool('back', 'Executando um comando', 'command'))).toBe(items)
    expect(applyActivityEvent(items, reply('back'))).toBe(items)
  })

  it("clears on Alfred's reply", () => {
    expect(applyActivityEvent(run([tool('alfred', 'a', 'tool')]), reply('alfred'))).toEqual([])
  })
})
