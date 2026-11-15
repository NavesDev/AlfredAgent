// Mirrors the bus events published by the server (see docs/ARCHITECTURE.md#event-bus).

import type { components } from './schema'

export type SessionView = components['schemas']['SessionView']
export type SubagentView = components['schemas']['SubagentView']
export type Project = components['schemas']['Project']
export type Workspace = components['schemas']['Workspace']
export type SettingsView = components['schemas']['SettingsView']
export type UsageView = components['schemas']['UsageView']
export type RateLimit = components['schemas']['RateLimit']
export type Phase = NonNullable<SessionView['phase']>

/** Mirrors server/infra/claude/activity.py's Action. */
export type ActivityAction =
  | 'delegate'
  | 'session'
  | 'project'
  | 'command'
  | 'files_read'
  | 'files_edit'
  | 'web_search'
  | 'web_page'
  | 'email_read'
  | 'email_send'
  | 'calendar_read'
  | 'calendar_write'
  | 'drive'
  | 'browser'
  | 'tool'

export type VoiceState = 'idle' | 'listening' | 'transcribing' | 'thinking' | 'speaking'

type Base = { ts: number }

export type AlfredEvent = Base &
  (
    | { type: 'voice_state'; state: VoiceState }
    | { type: 'audio_level'; source: 'mic' | 'tts'; level: number; bands?: number[] }
    | { type: 'transcript'; text: string; source: 'voice' | 'web' }
    | { type: 'alfred_reply'; session: string; text: string; summary: string }
    | { type: 'alfred_cleared' }
    | {
        type: 'agent_progress'
        session: string
        kind: 'text' | 'tool'
        content: string
        /** What Alfred is doing, in pt-BR (tools only), e.g. "Analisando seus e-mails". */
        label?: string
        /** The kind of step, for the activity cards (tools only), e.g. "web_search". */
        action?: ActivityAction
        /** Search query, site host or command description, tools only. */
        detail?: string | null
        /** What a coding session is doing, from the tool: exploring, editing or running. */
        phase?: Phase | null
      }
    | { type: 'error'; where: string; message: string }
    | { type: 'session_created'; session: SessionView }
    | { type: 'session_status'; session: SessionView }
    | { type: 'session_cleared'; session: SessionView }
    | { type: 'session_deleted'; name: string }
    | {
        type: 'subagent_started'
        session: string
        id: string
        subagent_type: string | null
        description: string
      }
    | { type: 'subagent_progress'; session: string; id: string; last_tool: string | null }
    | {
        type: 'subagent_finished'
        session: string
        id: string
        status: SubagentView['status']
      }
    | { type: 'project_created'; project: Project }
    | { type: 'project_updated'; project: Project }
    | { type: 'project_deleted'; id: number }
    | { type: 'settings_updated'; settings: SettingsView }
    | {
        type: 'rate_limit'
        window: string
        status: RateLimit['status']
        utilization: number | null
        resets_at: number | null
      }
  )

export type EventOf<T extends AlfredEvent['type']> = Extract<AlfredEvent, { type: T }>
