import type { AlfredEvent, UnstampedEvent } from '../api/events'
import { emit } from '../hooks/useEvents'
import { sessionView as session } from './sessionView'

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

const RECURVE = {
  kind: 'implementacao',
  label: 'Implementação',
  model: 'opus',
  project: 'Recurve',
  cwd: '~/dev/recurve-api-wt/cancel',
}
const BACK = { ...RECURVE, workspace: 'cancel', branch: 'cancel', connected: true }
const IMPL_TASK = 'cria o endpoint de cancelamento'
const busyBack = (over: Partial<Parameters<typeof session>[1]> = {}) =>
  session('back', { ...BACK, status: 'busy', task: IMPL_TASK, ...over })
const tool = (content: string, detail: string, phase: 'exploring' | 'editing' | 'running') =>
  ({ type: 'agent_progress', session: 'back', kind: 'tool', content, detail, phase }) as const
const EXPLORE = {
  id: 'k1',
  type: 'Explore',
  description: 'Acha o fluxo de reembolso',
  status: 'running' as const,
}

const IMPLEMENTATION: Step[] = [
  { at: 200, event: { type: 'session_created', session: session('back', BACK) } },
  {
    at: 250,
    event: {
      type: 'session_created',
      session: session('front', { ...RECURVE, workspace: 'front', cwd: '~/dev/recurve-web' }),
    },
  },
  {
    at: 1200,
    event: {
      type: 'session_status',
      session: busyBack({ phase: 'exploring', activity: 'Lendo arquivos' }),
    },
  },
  { at: 1300, event: tool('Grep', 'refund', 'exploring') },
  { at: 1900, event: tool('Read', 'billing.py', 'exploring') },
  {
    at: 3000,
    event: {
      type: 'subagent_started',
      session: 'back',
      id: 'k1',
      subagent_type: 'Explore',
      description: EXPLORE.description,
    },
  },
  {
    at: 3050,
    event: {
      type: 'session_status',
      session: busyBack({ phase: 'exploring', subagents: [EXPLORE] }),
    },
  },
  { at: 4600, event: tool('Edit', 'billing.py', 'editing') },
  {
    at: 4650,
    event: {
      type: 'session_status',
      session: busyBack({ phase: 'editing', activity: 'Editando arquivos', subagents: [EXPLORE] }),
    },
  },
  {
    at: 5600,
    event: { type: 'subagent_finished', session: 'back', id: 'k1', status: 'completed' },
  },
  {
    at: 5650,
    event: {
      type: 'session_status',
      session: busyBack({
        phase: 'editing',
        activity: 'Editando arquivos',
        subagents: [{ ...EXPLORE, status: 'completed' }],
      }),
    },
  },
  { at: 6400, event: tool('Bash', 'Roda os testes', 'running') },
  {
    at: 6450,
    event: {
      type: 'session_status',
      session: busyBack({ phase: 'running', activity: 'Executando um comando' }),
    },
  },
  {
    at: 10200,
    event: {
      type: 'session_status',
      session: session('back', {
        ...BACK,
        tasks_done: 1,
        tokens: 38200,
        last_summary: 'Endpoint criado e testes passando.',
      }),
    },
  },
]

const SCRIPT: Step[] = [
  ...SESSIONS,
  ...IMPLEMENTATION,
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
