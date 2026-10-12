import type { SessionView } from '../../../api/events'
import { lookOf, type Look } from '../lib/look'
import { useFlash } from './useFlash'

/** How this session is drawn now, including one-off flashes from the /ws. */
export function useLook(session: SessionView): Look {
  const { flash, now } = useFlash(session)
  return lookOf(session, flash, now)
}
