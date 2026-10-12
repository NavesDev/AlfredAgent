import type { ActivityAction, AlfredEvent } from '../../../api/events'

export type Activity = { id: number; action: ActivityAction; label: string; detail: string | null }

/** Cards on screen; one more is kept so the oldest can slide out. */
export const SHOWN = 3
const KEEP = SHOWN + 1

/** What Alfred himself is doing (tools), kept until his reply; delegated sessions show elsewhere. */
export function applyActivityEvent(items: Activity[], event: AlfredEvent): Activity[] {
  if (event.type === 'agent_progress' && event.kind === 'tool') {
    if (event.session !== 'alfred') return items
    const action = event.action ?? 'tool'
    const label = event.label ?? event.content
    const detail = event.detail ?? null
    const last = items.at(-1)
    if (last?.action === action) {
      // the same kind of step again (another search, another page): refresh its card
      if (last.label === label && last.detail === detail) return items
      return [...items.slice(0, -1), { ...last, label, detail }]
    }
    return [...items, { id: event.ts, action, label, detail }].slice(-KEEP)
  }
  if (event.type === 'alfred_reply' && event.session !== 'alfred') return items
  if (
    event.type === 'alfred_reply' ||
    event.type === 'error' ||
    event.type === 'transcript' ||
    (event.type === 'voice_state' && event.state === 'listening')
  ) {
    return items.length ? [] : items
  }
  return items
}
