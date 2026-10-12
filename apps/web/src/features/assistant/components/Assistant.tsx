import type { Ref } from 'react'
import { useActivity } from '../hooks/useActivity'
import { useVoice } from '../hooks/useVoice'
import { ActivityList } from './ActivityList'
import { Orb } from './Orb'
import { VoiceStatus } from './VoiceStatus'

type Props = {
  caption: string | null
  /** The orb's box, so the dashboard can tie the agent sessions to it. */
  orbRef?: Ref<HTMLDivElement>
}

export function Assistant({ caption, orbRef }: Props) {
  const { state, level } = useVoice()
  const activity = useActivity()
  return (
    <div className="flex h-full flex-col items-center gap-4 px-4 pb-6">
      <div ref={orbRef} className="min-h-0 w-full max-w-[640px] flex-1">
        <Orb state={state} level={level} pulse={activity.at(-1)?.id ?? 0} />
      </div>
      <VoiceStatus state={state} />
      <ActivityList items={activity} />
      <p className="min-h-12 max-w-xl text-center text-lg text-balance text-gray-100/90">
        {caption}
      </p>
    </div>
  )
}
