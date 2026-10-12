import type { AlfredEvent } from '../../../api/events'
import type { TranscriptState, Turn } from '../types'

const MAX_TURNS = 200

export const initialTranscript: TranscriptState = { turns: [], transcribingAt: null, nextId: 1 }

const round = (s: number) => Math.round(s * 100) / 100

function isOpen(turn: Turn | undefined): turn is Turn {
  return !!turn && turn.reply === null && turn.error === null
}

function updateLast(state: TranscriptState, patch: (turn: Turn) => Partial<Turn>): TranscriptState {
  const last = state.turns.at(-1)
  if (!isOpen(last)) return state
  return { ...state, turns: [...state.turns.slice(0, -1), { ...last, ...patch(last) }] }
}

function push(state: TranscriptState, turn: Omit<Turn, 'id'>): TranscriptState {
  const turns = [...state.turns, { ...turn, id: state.nextId }].slice(-MAX_TURNS)
  return { ...state, turns, nextId: state.nextId + 1 }
}

const blank = (ts: number): Omit<Turn, 'id'> => ({
  heardAt: ts,
  source: null,
  userText: null,
  sttS: null,
  steps: [],
  firstSpeechS: null,
  replyS: null,
  session: null,
  summary: null,
  reply: null,
  error: null,
})

export function reduceTranscript(state: TranscriptState, event: AlfredEvent): TranscriptState {
  switch (event.type) {
    case 'voice_state':
      if (event.state === 'transcribing') return { ...state, transcribingAt: event.ts }
      if (event.state === 'speaking')
        return updateLast(state, (t) =>
          t.firstSpeechS === null ? { firstSpeechS: round(event.ts - t.heardAt) } : {},
        )
      return state
    case 'transcript':
      return push(
        { ...state, transcribingAt: null },
        {
          ...blank(event.ts),
          source: event.source,
          userText: event.text,
          sttS: state.transcribingAt === null ? null : round(event.ts - state.transcribingAt),
        },
      )
    case 'agent_progress':
      if (event.session !== 'alfred') return state // delegated work shows up live, not here
      return updateLast(state, (t) => ({
        steps: [
          ...t.steps,
          {
            ts: event.ts,
            kind: event.kind,
            content: event.content,
            label: event.label ?? event.content,
            detail: event.detail ?? null,
          },
        ],
      }))
    case 'alfred_reply': {
      const reply = { reply: event.text, summary: event.summary || null, session: event.session }
      if (event.session !== 'alfred' || !isOpen(state.turns.at(-1)))
        return push(state, { ...blank(event.ts), ...reply })
      return updateLast(state, (t) => ({ ...reply, replyS: round(event.ts - t.heardAt) }))
    }
    case 'alfred_cleared': // a fresh conversation starts with an empty transcript
      return { ...initialTranscript, nextId: state.nextId }
    case 'error': {
      const error = `${event.where}: ${event.message}`
      if (!isOpen(state.turns.at(-1))) return push(state, { ...blank(event.ts), error })
      return updateLast(state, () => ({ error }))
    }
    default:
      return state
  }
}

export const describe = (label: string, detail: string | null) =>
  detail ? `${label}: ${detail}` : label

export const speaker = (session: string | null) =>
  !session || session === 'alfred' ? 'Alfred' : `Alfred · ${session}`

const seconds = (s: number | null) => (s === null ? '–' : `${s.toFixed(2)}s`)

/** Plain-text export for pasting into notes or an issue. */
export function toMarkdown(turns: Turn[]): string {
  return turns
    .map((t) => {
      const when = new Date(t.heardAt * 1000).toLocaleTimeString('pt-BR')
      const lines = [`### ${when}`]
      if (t.userText) lines.push(`**Você (${t.source}):** ${t.userText}`)
      for (const step of t.steps.filter((s) => s.kind === 'tool'))
        lines.push(`- ${describe(step.label, step.detail)} (${step.content})`)
      if (t.summary) lines.push(`**${speaker(t.session)} (falado):** ${t.summary}`)
      if (t.reply) lines.push('', t.reply)
      if (t.error) lines.push(`**Erro:** ${t.error}`)
      lines.push(
        '',
        `_STT ${seconds(t.sttS)} · 1ª fala ${seconds(t.firstSpeechS)} · resposta ${seconds(t.replyS)}_`,
      )
      return lines.join('\n')
    })
    .join('\n\n')
}
