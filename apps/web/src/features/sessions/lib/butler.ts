import type { AlfredEvent, SessionView } from '../../../api/events'

// What the butler (implementation sessions) is doing. The base state follows the session;
// a flash plays once on top of it: a letter when a subagent is called, the hat trick when a
// task ends well. "queued" is the wait for a free slot; "waiting" is drawn but has no trigger
// until permissions land (F5).

export type ButlerState =
  | 'sleeping'
  | 'exploring'
  | 'editing'
  | 'running'
  | 'delegating'
  | 'done'
  | 'error'
  | 'waiting'
  | 'queued'

export type FlashState = 'delegating' | 'done'
export type Flash = { state: FlashState; at: number }

export const FLASH_MS: Record<FlashState, number> = { delegating: 1500, done: 3000 }

export function baseState(session: SessionView): ButlerState {
  if (session.waiting) return 'queued'
  if (session.status === 'error') return 'error'
  if (session.status === 'idle') return 'sleeping'
  return session.phase ?? 'editing'
}

/** The flash an event starts for this session, given its status before the event. */
export function flashFor(
  name: string,
  before: SessionView['status'] | undefined,
  event: AlfredEvent,
): FlashState | null {
  if (event.type === 'subagent_started' && event.session === name) return 'delegating'
  if (event.type === 'session_status' && event.session.name === name) {
    if (before === 'busy' && event.session.status === 'idle') return 'done'
  }
  return null
}

export function butlerState(session: SessionView, flash: Flash | null, now: number): ButlerState {
  if (
    !session.waiting &&
    session.status !== 'error' &&
    flash &&
    now - flash.at < FLASH_MS[flash.state]
  ) {
    return flash.state
  }
  return baseState(session)
}
