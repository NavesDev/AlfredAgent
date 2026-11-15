import { useRef, useState } from 'react'
import type { VoiceState } from '../../../api/events'
import { useEvents } from '../../../hooks/useEvents'

export type Level = { value: number; bands: number[]; at: number }

/** Voice state drives re-renders; the audio level lives in a ref so the orb reads it per frame. */
export function useVoice() {
  const [state, setState] = useState<VoiceState>('idle')
  const level = useRef<Level>({ value: 0, bands: [], at: 0 })
  useEvents((event) => {
    if (event.type === 'voice_state') setState(event.state)
    else if (event.type === 'audio_level')
      level.current = { value: event.level, bands: event.bands ?? [], at: performance.now() }
  })
  return { state, level }
}
