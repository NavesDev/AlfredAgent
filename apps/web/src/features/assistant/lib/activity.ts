import type { AlfredEvent } from '../../../api/events'

export type Activity = { id: number; text: string }

const KEEP = 3

/** What Alfred himself is doing (tools), kept until his reply; delegated sessions show elsewhere. */
export function applyActivityEvent(items: Activity[], event: AlfredEvent): Activity[] {
  if (event.type === 'agent_progress' && event.kind === 'tool') {
    if (event.session !== 'alfred') return items
    const label = event.label ?? event.content
    const text = event.detail ? `${label}: ${event.detail}` : label
    return items.at(-1)?.text === text ? items : [...items, { id: event.ts, text }].slice(-KEEP)
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
