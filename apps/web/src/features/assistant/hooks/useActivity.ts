import { useState } from 'react'
import { useEvents } from '../../../hooks/useEvents'
import { applyActivityEvent, type Activity } from '../lib/activity'

export type { Activity }

/** What Alfred is doing right now (tools), kept until the reply arrives. */
export function useActivity(): Activity[] {
  const [items, setItems] = useState<Activity[]>([])
  useEvents((event) => setItems((prev) => applyActivityEvent(prev, event)))
  return items
}
