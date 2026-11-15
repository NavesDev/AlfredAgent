import { useEffect, useState } from 'react'
import { panelOutOfSight } from '../../../lib/desktop'

const POLL_MS = 400

/** Whether the panel window is minimized or in the tray; only polled while `active`. */
export function usePanelOutOfSight(active: boolean): boolean {
  const [outOfSight, setOutOfSight] = useState(false)
  useEffect(() => {
    if (!active) return
    let alive = true
    const check = () =>
      panelOutOfSight()
        .then((value) => alive && setOutOfSight(value))
        .catch(() => alive && setOutOfSight(false))
    void check()
    const timer = setInterval(check, POLL_MS)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [active])
  return active && outOfSight
}
