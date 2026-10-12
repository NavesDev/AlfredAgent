import { useEffect, useRef, useState } from 'react'
import type { SessionView } from '../../../api/events'
import { useEvents } from '../../../hooks/useEvents'
import { FLASH_MS, flashFor, type Flash } from '../lib/butler'

/** The latest one-off flash of this session from the /ws, and a clock that moves at its edges. */
export function useFlash(session: SessionView): { flash: Flash | null; now: number } {
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

  return { flash, now }
}
