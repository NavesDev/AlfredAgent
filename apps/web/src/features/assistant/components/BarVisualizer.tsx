/*
 * Adapted from the Bar Visualizer of ElevenLabs UI (https://ui.elevenlabs.io/docs/components/bar-visualizer).
 * Copyright (c) 2025 Eleven Labs Inc., MIT License. Fed by the server's frequency bands instead of a MediaStream.
 */
import { useEffect, useMemo, useState, type RefObject } from 'react'
import type { VoiceState } from '../../../api/events'
import type { Level } from '../hooks/useVoice'
import { arrangeBands, bandsFromLevel, BAR_COUNT, barHeight, barSequence } from '../lib/bars'

/** Bands older than this mean the voice paused; the bars fall back to the state animation. */
const BANDS_TTL_MS = 250

const BEAT_MS: Partial<Record<VoiceState, number>> = {
  thinking: 150,
  transcribing: 150,
  listening: 500,
}

/** Samples the latest bands once per frame (or fakes them from the level), null when stale. */
function useLiveBands(level: RefObject<Level>): number[] | null {
  const [bands, setBands] = useState<number[] | null>(null)
  useEffect(() => {
    let frame = 0
    let last: Level | null = null
    const tick = () => {
      const current = level.current
      const now = performance.now()
      const fresh = now - current.at < BANDS_TTL_MS
      if (!fresh) setBands(null)
      else if (current !== last)
        setBands(current.bands.length ? current.bands : bandsFromLevel(current.value, now / 1000))
      last = current
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [level])
  return bands
}

/** Steps through the state's highlight sequence. */
function useBeat(state: VoiceState): number[] {
  const sequence = useMemo(() => barSequence(state), [state])
  const [index, setIndex] = useState(0)
  useEffect(() => {
    const ms = BEAT_MS[state]
    if (!ms) return
    const timer = setInterval(() => setIndex((i) => (i + 1) % sequence.length), ms)
    return () => clearInterval(timer)
  }, [state, sequence])
  return sequence[index % sequence.length] ?? []
}

type Props = { state: VoiceState; level: RefObject<Level> }

/** Rounded bars that follow the voice's frequency bands, or a quiet beat when there is no audio. */
export function BarVisualizer({ state, level }: Props) {
  const live = useLiveBands(level)
  const lit = useBeat(state)
  const bars = live ? arrangeBands(live) : new Array<number>(BAR_COUNT).fill(0)
  return (
    <div aria-hidden className="flex h-7 items-center gap-[3px]">
      {bars.map((value, i) => (
        <span
          key={i}
          style={{ height: `${barHeight(value)}%` }}
          className={`w-[5px] rounded-full transition-[height,background-color] duration-150 ${
            live || lit.includes(i) ? 'bg-ink' : 'bg-ink/30'
          }`}
        />
      ))}
    </div>
  )
}
