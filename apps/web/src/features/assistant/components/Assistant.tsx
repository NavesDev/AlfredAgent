import type { Ref } from 'react'
import type { Activity } from '../hooks/useActivity'
import { LIFT_TRANSITION } from '../../../lib/motion'
import { useVoice } from '../hooks/useVoice'
import { ActivityCards } from './ActivityCards'
import { Orb } from './Orb'
import { VoiceStatus } from './VoiceStatus'

type Props = {
  caption: string | null
  activity: Activity[]
  /** How far the orb rises to make room for the activity cards, in px. */
  lift: number
  /** The orb's box, so the dashboard can tie the agent sessions to it. */
  orbRef?: Ref<HTMLDivElement>
}

export function Assistant({ caption, activity, lift, orbRef }: Props) {
  const { state, level } = useVoice()
  return (
    <div className="flex h-full flex-col items-center gap-4 px-4 pb-6">
      <div className="relative min-h-0 w-full max-w-[640px] flex-1">
        {/* moved, never resized: the canvas and the sessions tied to it rise together */}
        <div
          ref={orbRef}
          style={{ top: -lift, bottom: lift, transition: LIFT_TRANSITION }}
          className="absolute inset-x-0"
        >
          <Orb state={state} level={level} pulse={activity.at(-1)?.id ?? 0} />
        </div>
        <ActivityCards items={activity} />
      </div>
      <VoiceStatus state={state} />
      <p className="min-h-12 max-w-xl text-center text-lg text-balance text-gray-100/90">
        {caption}
      </p>
    </div>
  )
}
