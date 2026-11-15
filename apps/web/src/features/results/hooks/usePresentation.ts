import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../../../api/client'
import type { PresentMode, ResultView } from '../../../api/events'
import { useEvents } from '../../../hooks/useEvents'

export type Presentation = { result: ResultView; mode: PresentMode }

/** What is on screen now, from result_presented / presentation_closed on the /ws. */
export function usePresentation() {
  const [current, setCurrent] = useState<Presentation | null>(null)
  useEvents((event) => {
    if (event.type === 'result_presented') setCurrent({ result: event.result, mode: event.mode })
    if (event.type === 'presentation_closed') setCurrent(null)
  })
  const closeAll = useMutation({
    mutationFn: () => api<void>('/api/presentation/close', { method: 'POST' }),
  })
  return {
    current,
    /** Closes it everywhere (overlay, panel, viewer). */
    close: () => (setCurrent(null), closeAll.mutate()),
    /** Hides it here only (the card leaving on its own). */
    dismiss: () => setCurrent(null),
  }
}
