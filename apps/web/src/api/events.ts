// Mirrors the bus events published by the server (see docs/ARCHITECTURE.md#event-bus).

import type { components } from './schema'

export type SessionView = components['schemas']['SessionView']

export type VoiceState = 'idle' | 'listening' | 'transcribing' | 'thinking' | 'speaking'

type Base = { ts: number }

export type AlfredEvent = Base &
  (
    | { type: 'voice_state'; state: VoiceState }
    | { type: 'audio_level'; source: 'mic' | 'tts'; level: number }
    | { type: 'transcript'; text: string; source: 'voice' | 'web' }
    | { type: 'alfred_reply'; session: string; text: string; summary: string }
    | {
        type: 'agent_progress'
        session: string
        kind: 'text' | 'tool'
        content: string
        /** What Alfred is doing, in pt-BR (tools only), e.g. "Analisando seus e-mails". */
        label?: string
        /** Search query, site host or command description, tools only. */
        detail?: string | null
      }
    | { type: 'error'; where: string; message: string }
    | { type: 'session_created'; session: SessionView }
    | { type: 'session_status'; session: SessionView }
    | { type: 'session_cleared'; session: SessionView }
    | { type: 'session_deleted'; name: string }
  )

export type EventOf<T extends AlfredEvent['type']> = Extract<AlfredEvent, { type: T }>

/** An event before the server stamps it, e.g. for the demo script. */
export type UnstampedEvent = AlfredEvent extends infer E
  ? E extends AlfredEvent
    ? Omit<E, 'ts'>
    : never
  : never
