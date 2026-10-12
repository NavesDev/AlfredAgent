import type { AlfredEvent, SessionView } from '../../../api/events'

/** Applies a session_* event from the /ws to the list the panel shows. */
export function applySessionEvent(list: SessionView[], event: AlfredEvent): SessionView[] {
  switch (event.type) {
    case 'session_created':
    case 'session_status':
    case 'session_cleared': {
      const { session } = event
      const i = list.findIndex((s) => s.name === session.name)
      return i < 0 ? [...list, session] : list.with(i, session)
    }
    case 'session_deleted':
      return list.filter((s) => s.name !== event.name)
    default:
      return list
  }
}
