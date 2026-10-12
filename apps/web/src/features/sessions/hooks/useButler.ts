import { useEffect, useRef, useState } from 'react'
import type { SessionView } from '../../../api/events'
import { useEvents } from '../../../hooks/useEvents'
import { butlerState, FLASH_MS, flashFor, type ButlerState, type Flash } from '../lib/butler'

/** What the butler of this session shows now, including one-off flashes from the /ws. */
export function useButler(session: SessionView): ButlerState {
  const before = useRef(session.status)
  const [flash, setFlash] = useState<Flash | null>(null)
  const [now, setNow] = useState(0) // moves at a flash's start and end; renders stay pure

  useEvents((event) => {
    const next = flashFor(session.name, before.current, event)
    if (event.type === 'session_status' && event.session.name === session.name) {
      before.current = event.session.status
    }
    if (next) {
      const at = Date.now()
      setFlash({ state: next, at })
      setNow(at)
    }
  })

  useEffect(() => {
    if (!flash) return
    const timer = setTimeout(() => setNow(Date.now()), FLASH_MS[flash.state])
    return () => clearTimeout(timer)
  }, [flash])

  return butlerState(session, flash, now)
}
