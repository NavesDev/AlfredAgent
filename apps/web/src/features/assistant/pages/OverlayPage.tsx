import { useEffect, useState } from 'react'
import { appWindow, setPillShown } from '../../../lib/desktop'
import { VoicePill } from '../components/VoicePill'
import { usePanelOutOfSight } from '../hooks/usePanelOutOfSight'
import { useVoice } from '../hooks/useVoice'

/** Time the pill takes to fade out before it unmounts (matches animate-pill-out). */
const LEAVE_MS = 220

/**
 * The desktop overlay window: transparent and always on top.
 * Shows the voice pill while Alfred is busy and the panel window is out of sight.
 * The shell lets clicks through except over the shown pill, which can be dragged; it keeps
 * the pill on screen and remembers where it was left. The pill is pinned to the window's
 * top-right corner with a fixed size: apps/desktop's PILL constant must match.
 */
export function OverlayPage() {
  const { state, level } = useVoice()
  const active = state !== 'idle'
  const shown = usePanelOutOfSight(active)
  const [wasShown, setWasShown] = useState(shown)
  const [leaving, setLeaving] = useState(false)
  if (shown !== wasShown) {
    setWasShown(shown)
    setLeaving(!shown)
  }

  useEffect(() => {
    document.documentElement.classList.add('overlay')
    return () => document.documentElement.classList.remove('overlay')
  }, [])

  useEffect(() => {
    void setPillShown(shown).catch(() => {})
  }, [shown])

  useEffect(() => {
    if (!leaving) return
    const timer = setTimeout(() => setLeaving(false), LEAVE_MS)
    return () => clearTimeout(timer)
  }, [leaving])

  return (
    <div className="flex h-full items-start justify-end p-2">
      {(shown || leaving) && (
        <VoicePill
          state={state}
          level={level}
          leaving={!shown}
          onDragStart={() => void appWindow().startDragging()}
        />
      )}
    </div>
  )
}
