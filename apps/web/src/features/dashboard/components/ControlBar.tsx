import type { ReactNode } from 'react'
import type { VoiceState } from '../../../api/events'
import { Segmented } from '../../../components/controls'
import { Mic, Plus, Stop, Transcript } from '../../../components/icons'
import type { Family } from '../lib/alfredModel'

const VOICE: Record<VoiceState, { label: string; hint: string; mic: string; meter: string }> = {
  idle: {
    label: 'Em espera',
    hint: 'Diga “Alfred”',
    mic: 'bg-fill-on text-ink',
    meter: 'w-[18%] bg-ink-2',
  },
  listening: {
    label: 'Ouvindo',
    hint: 'Pode falar',
    mic: 'bg-white text-black',
    meter: 'w-[70%] bg-white animate-pulse',
  },
  transcribing: {
    label: 'Transcrevendo',
    hint: 'Um instante',
    mic: 'bg-fill-on text-ink',
    meter: 'w-[40%] bg-ink-2 animate-pulse',
  },
  thinking: {
    label: 'Pensando',
    hint: 'Um instante',
    mic: 'bg-fill-on text-ink',
    meter: 'w-[35%] bg-ink-2 animate-pulse',
  },
  speaking: {
    label: 'Falando',
    hint: 'Respondendo',
    mic: 'bg-apple-blue text-white',
    meter: 'w-[60%] bg-apple-blue animate-pulse',
  },
}

type Props = {
  state: VoiceState
  family: Family | null
  onFamily: (family: Family) => void
  onNewConversation: () => void
  clearing?: boolean
  transcript: boolean
  onTranscript: () => void
  /** Extra controls at the end (usage meter). */
  children?: ReactNode
}

/** The ornament under the orb: voice state, Alfred's model and the conversation controls. */
export function ControlBar(p: Props) {
  const v = VOICE[p.state]
  return (
    <div className="glass flex max-w-full flex-wrap items-center justify-center gap-2.5 rounded-[28px] p-2 sm:flex-nowrap sm:rounded-full">
      <span
        aria-hidden
        className={`grid size-12 shrink-0 place-items-center rounded-full transition-colors ${v.mic}`}
      >
        {p.state === 'speaking' ? <Stop className="size-5" /> : <Mic className="size-5" />}
      </span>
      <div aria-live="polite" className="grid min-w-28 px-1">
        <span className="text-sm font-semibold">{v.label}</span>
        <span className="text-[11.5px] text-ink-2">{v.hint}</span>
        <span className="mt-1.5 h-[3px] overflow-hidden rounded-full bg-fill">
          <span
            className={`block h-full rounded-full transition-[width] duration-500 ${v.meter}`}
          />
        </span>
      </div>
      <Segmented
        label="Modelo do Alfred"
        value={p.family ?? ('' as Family)}
        onChange={p.onFamily}
        options={[
          { value: 'opus', label: 'Opus' },
          { value: 'sonnet', label: 'Sonnet' },
          { value: 'haiku', label: 'Haiku' },
        ]}
      />
      <button
        type="button"
        onClick={p.onNewConversation}
        disabled={p.clearing}
        aria-label="Nova conversa"
        title="Esquece a conversa de hoje; espera a resposta em andamento terminar"
        className="grid size-10 shrink-0 place-items-center rounded-full hover:bg-fill disabled:opacity-40"
      >
        <Plus className="size-[18px]" />
      </button>
      <button
        type="button"
        onClick={p.onTranscript}
        aria-pressed={p.transcript}
        aria-label="Transcrição"
        title="Transcrição (T)"
        className="grid size-10 shrink-0 place-items-center rounded-full hover:bg-fill aria-pressed:bg-fill-on"
      >
        <Transcript className="size-[18px]" />
      </button>
      {p.children}
    </div>
  )
}
