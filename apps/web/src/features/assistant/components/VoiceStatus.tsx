import type { VoiceState } from '../../../api/events'

const LABELS: Record<VoiceState, { text: string; dot: string }> = {
  idle: { text: 'Em espera · diga “Alfred”', dot: 'bg-indigo-400/60' },
  listening: { text: 'Ouvindo', dot: 'bg-teal-300' },
  transcribing: { text: 'Transcrevendo', dot: 'bg-purple-400' },
  thinking: { text: 'Pensando', dot: 'bg-amber-400' },
  speaking: { text: 'Falando', dot: 'bg-emerald-400' },
}

export function VoiceStatus({ state }: { state: VoiceState }) {
  const { text, dot } = LABELS[state]
  return (
    <div
      className="flex items-center gap-2.5 text-sm tracking-wide text-gray-300"
      aria-live="polite"
    >
      <span className={`size-2 rounded-full ${dot} ${state === 'idle' ? '' : 'animate-pulse'}`} />
      {text}
    </div>
  )
}
