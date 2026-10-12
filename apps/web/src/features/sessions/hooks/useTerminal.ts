import { useState } from 'react'
import { useEvents } from '../../../hooks/useEvents'
import { applyTerminalEvent, type TerminalLines } from '../lib/terminal'

/** Last tool calls per session, for the hover terminal. Starts empty on each page load. */
export function useTerminal(): TerminalLines {
  const [lines, setLines] = useState<TerminalLines>({})
  useEvents((event) => setLines((current) => applyTerminalEvent(current, event)))
  return lines
}
