import type { AlfredEvent } from '../../../api/events'

// The little terminal shown when hovering an implementation session: its last tool calls.

export const TERMINAL_LINES = 6

export type TerminalLines = Record<string, string[]>

export function applyTerminalEvent(lines: TerminalLines, event: AlfredEvent): TerminalLines {
  if (event.type === 'session_deleted') {
    const { [event.name]: _, ...rest } = lines
    return rest
  }
  if (event.type !== 'agent_progress' || event.kind !== 'tool' || event.session === 'alfred') {
    return lines
  }
  const line = `› ${event.content}${event.detail ? ` ${event.detail}` : ''}`
  const previous = lines[event.session] ?? []
  return { ...lines, [event.session]: [...previous, line].slice(-TERMINAL_LINES) }
}
