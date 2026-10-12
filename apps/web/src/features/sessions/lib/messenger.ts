import type { SessionView } from '../../../api/events'
import { FLASH_MS, type Flash } from './butler'

// What the messenger (general sessions) is doing. Waiting for a free slot comes first: the
// task is already sent, only the slot is missing. "done" plays once when a task ends well.

export type MessengerState = 'sleeping' | 'carrying' | 'queued' | 'done' | 'error'

export function messengerState(
  session: SessionView,
  flash: Flash | null,
  now: number,
): MessengerState {
  if (session.waiting) return 'queued'
  if (session.status === 'error') return 'error'
  if (flash?.state === 'done' && now - flash.at < FLASH_MS.done) return 'done'
  return session.status === 'busy' ? 'carrying' : 'sleeping'
}
