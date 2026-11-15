import { useState, type RefObject } from 'react'
import type { VoiceState } from '../../../api/events'
import type { Level } from '../hooks/useVoice'
import { hasWebGL2, orbMotion } from '../lib/orb'
import { BarVisualizer } from './BarVisualizer'
import { CssOrb } from './CssOrb'
import Strands from './strands/Strands'

const LABEL: Record<VoiceState, string> = {
  idle: 'Alfred em espera',
  listening: 'Alfred ouvindo',
  transcribing: 'Alfred transcrevendo',
  thinking: 'Alfred pensando',
  speaking: 'Alfred falando',
}

type Props = {
  state: VoiceState
  level: RefObject<Level>
  leaving: boolean
}

/** The floating pill: a small Alfred orb and the bar visualizer, on dark glass. It stays where
 * the position preset puts it (Settings → Geral); it is not dragged. */
export function VoicePill({ state, level, leaving }: Props) {
  const [webgl] = useState(hasWebGL2)
  const motion = orbMotion(state, null)
  return (
    <div
      role="img"
      aria-label={LABEL[state]}
      className={`flex h-12 w-[148px] shrink-0 items-center gap-3 select-none rounded-full border border-white/15 bg-[rgb(22_22_26/0.82)] py-1.5 pr-4 pl-1.5 shadow-[inset_0_1px_0_rgb(255_255_255/0.18),0_6px_16px_rgb(0_0_0/0.45)] ${
        leaving ? 'animate-pill-out' : 'animate-pill-in'
      }`}
    >
      <div className="size-9 shrink-0">
        {webgl ? (
          <Strands {...motion} interactive={false} intro={false} />
        ) : (
          <CssOrb motion={motion} />
        )}
      </div>
      <BarVisualizer state={state} level={level} />
    </div>
  )
}
