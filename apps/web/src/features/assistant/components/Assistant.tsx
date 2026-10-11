import { useVoice } from '../hooks/useVoice'
import { Orb } from './Orb'
import { VoiceStatus } from './VoiceStatus'

export function Assistant({ caption }: { caption: string | null }) {
  const { state, level } = useVoice()
  return (
    <div className="flex h-full flex-col items-center gap-4 px-4 pb-6">
      <div className="min-h-0 w-full max-w-[640px] flex-1">
        <Orb state={state} level={level} />
      </div>
      <VoiceStatus state={state} />
      <p className="min-h-12 max-w-xl text-center text-lg text-balance text-gray-100/90">
        {caption}
      </p>
    </div>
  )
}
