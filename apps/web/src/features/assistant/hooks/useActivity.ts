import { useState } from 'react'
import { useEvents } from '../../../hooks/useEvents'

export type Activity = { id: number; text: string }

const KEEP = 3

/** What Alfred is doing right now (tools), kept until the reply arrives. */
export function useActivity(): Activity[] {
  const [items, setItems] = useState<Activity[]>([])
  useEvents((event) => {
    if (event.type === 'agent_progress' && event.kind === 'tool') {
      const label = event.label ?? event.content
      const text = event.detail ? `${label}: ${event.detail}` : label
      setItems((prev) =>
        prev.at(-1)?.text === text ? prev : [...prev, { id: event.ts, text }].slice(-KEEP),
      )
    } else if (
      event.type === 'alfred_reply' ||
      event.type === 'error' ||
      event.type === 'transcript' ||
      (event.type === 'voice_state' && event.state === 'listening')
    ) {
      setItems([])
    }
  })
  return items
}
