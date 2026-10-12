import type { SessionView } from '../../../api/events'
import { butlerState, type ButlerState, type Flash } from './butler'
import { messengerState, type MessengerState } from './messenger'

// How a session is drawn: the butler for implementation sessions, the messenger for the rest.
// Both read the same flash, so nodes and the details card stay in step.

export type Look =
  { figure: 'butler'; state: ButlerState } | { figure: 'messenger'; state: MessengerState }

const LINE: Record<ButlerState | MessengerState, string> = {
  sleeping: 'cochilando',
  exploring: 'explorando',
  editing: 'editando',
  running: 'rodando',
  delegating: 'chamando subagente',
  carrying: 'trabalhando',
  done: 'terminou',
  error: 'falhou na última tarefa',
  waiting: 'aguardando você',
  queued: 'na fila por uma vaga',
}

export function lookOf(session: SessionView, flash: Flash | null, now: number): Look {
  return session.kind === 'implementacao'
    ? { figure: 'butler', state: butlerState(session, flash, now) }
    : { figure: 'messenger', state: messengerState(session, flash, now) }
}

/** What the node says under the name: the state, plus the current activity while busy. */
export function lineOf(look: Look, session: SessionView): string {
  const detail = session.status === 'busy' && !session.waiting ? session.activity : null
  return `${LINE[look.state]}${detail ? ` · ${detail}` : ''}`
}
