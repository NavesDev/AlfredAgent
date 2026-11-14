import { useEffect, useState, type RefObject } from 'react'
import type { VoiceState } from '../../../api/events'
import type { Level } from '../hooks/useVoice'
import { hasWebGL2, orbMotion } from '../lib/orb'
import { CssOrb } from './CssOrb'
import Strands from './strands/Strands'

const LABEL: Record<VoiceState, string> = {
  idle: 'Alfred em espera',
  listening: 'Alfred ouvindo',
  transcribing: 'Alfred transcrevendo',
  thinking: 'Alfred pensando',
  speaking: 'Alfred falando',
}

/** Level events stop between utterances; older than this, the orb animates on its own. */
const LEVEL_TTL_MS = 250

/** Samples the audio level once per frame while the voice is live, null when it is stale. */
function useLiveLevel(level: RefObject<Level>, live: boolean): number | null {
  const [value, setValue] = useState<number | null>(null)
  useEffect(() => {
    if (!live) return
    let frame = 0
    const tick = () => {
      const { value: v, at } = level.current
      const fresh = performance.now() - at < LEVEL_TTL_MS
      setValue((old) => {
        const next = fresh ? Math.round(v * 50) / 50 : null
        return next === old ? old : next
      })
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [level, live])
  return live ? value : null
}

type Props = {
  state: VoiceState
  level: RefObject<Level>
  /** Overrides the WebGL2 check (tests, forced fallback). */
  webgl?: boolean
}

/** Alfred himself: the Strands glass orb, or its CSS stand-in where WebGL2 is missing. */
export function Orb({ state, level, webgl }: Props) {
  const [canDraw] = useState(() => webgl ?? hasWebGL2())
  const live = useLiveLevel(level, state === 'listening' || state === 'speaking')
  const motion = orbMotion(state, live)
  return (
    <div
      role="img"
      aria-label={LABEL[state]}
      data-renderer={canDraw ? 'webgl' : 'css'}
      className="aspect-square w-[min(100%,48vh,520px)]"
    >
      {canDraw ? <Strands {...motion} interactive={false} /> : <CssOrb motion={motion} />}
    </div>
  )
}
