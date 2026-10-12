import type { AlfredEvent, SessionView, UnstampedEvent } from '../api/events'
import { emit } from '../hooks/useEvents'

type Step = { at: number; event: UnstampedEvent }

const wave = (from: number, to: number, everyMs: number, source: 'mic' | 'tts'): Step[] =>
  Array.from({ length: Math.floor((to - from) / everyMs) }, (_, i) => ({
    at: from + i * everyMs,
    event: {
      type: 'audio_level',
      source,
      level: Math.max(0, 0.35 + 0.35 * Math.sin(i / 2.3) + (Math.random() - 0.5) * 0.4),
    },
  })) as Step[]

const session = (name: string, over: Partial<SessionView> = {}): SessionView => ({
  name,
  kind: 'geral',
  label: 'Geral',
  model: 'sonnet',
  cwd: '~',
  status: 'idle',
  task: null,
  activity: null,
  queue: 0,
  tasks_done: 0,
  tokens: 0,
  last_summary: null,
  protected: false,
  ...over,
})

const SISTEMA = { protected: true, tasks_done: 3, tokens: 11800, last_summary: 'Tela girada.' }
const TASK = 'baixa o instalador do Zoom'

const SESSIONS: Step[] = [
  { at: 0, event: { type: 'session_created', session: session('sistema', SISTEMA) } },
  {
    at: 300,
    event: { type: 'session_created', session: session('downloads', { cwd: '~/Downloads' }) },
  },
  {
    at: 800,
    event: {
      type: 'session_status',
      session: session('downloads', { cwd: '~/Downloads', status: 'busy', task: TASK }),
    },
  },
  {
    at: 1600,
    event: {
      type: 'session_status',
      session: session('downloads', {
        cwd: '~/Downloads',
        status: 'busy',
        task: TASK,
        activity: 'Executando um comando',
      }),
    },
  },
  {
    at: 8000,
    event: {
      type: 'session_status',
      session: session('downloads', {
        cwd: '~/Downloads',
        tasks_done: 1,
        tokens: 4200,
        last_summary: 'Instalador baixado.',
      }),
    },
  },
]

const SCRIPT: Step[] = [
  ...SESSIONS,
  { at: 0, event: { type: 'voice_state', state: 'listening' } },
  ...wave(100, 2400, 80, 'mic'),
  { at: 2500, event: { type: 'voice_state', state: 'transcribing' } },
  {
    at: 3300,
    event: {
      type: 'transcript',
      text: 'Alfred, qual a diferença entre JWT e sessão?',
      source: 'voice',
    },
  },
  { at: 3300, event: { type: 'voice_state', state: 'thinking' } },
  {
    at: 3900,
    event: {
      type: 'agent_progress',
      session: 'alfred',
      kind: 'tool',
      content: 'WebSearch',
      label: 'Pesquisando na web',
      detail: 'JWT vs sessão',
    },
  },
  {
    at: 4600,
    event: {
      type: 'agent_progress',
      session: 'alfred',
      kind: 'tool',
      content: 'WebFetch',
      label: 'Lendo uma página',
      detail: 'auth0.com',
    },
  },
  { at: 5200, event: { type: 'voice_state', state: 'speaking' } },
  ...wave(5200, 9200, 66, 'tts'),
  {
    at: 6000,
    event: {
      type: 'alfred_reply',
      session: 'alfred',
      summary: 'JWT guarda o estado no token; sessão guarda no servidor.',
      text: 'RESUMO: JWT guarda o estado no token; sessão guarda no servidor.\n\nCom JWT o servidor não precisa consultar nada para validar, mas revogar é difícil. Com sessão, o servidor mantém o estado e revogar é trivial.',
    },
  },
  { at: 9300, event: { type: 'voice_state', state: 'idle' } },
]

/** Plays a fake exchange through the event stream; returns a cancel function. */
export function playDemo(): () => void {
  const start = Date.now() / 1000
  const timers = SCRIPT.map(({ at, event }) =>
    setTimeout(() => emit({ ...event, ts: start + at / 1000 } as AlfredEvent), at),
  )
  return () => timers.forEach(clearTimeout)
}
