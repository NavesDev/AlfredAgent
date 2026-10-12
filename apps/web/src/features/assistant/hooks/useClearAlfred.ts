import { useMutation } from '@tanstack/react-query'
import { api } from '../../../api/client'

/** Forgets Alfred's conversation; the transcript empties on the alfred_cleared event. */
export function useClearAlfred() {
  return useMutation({
    mutationFn: () => api<void>('/api/alfred/clear', { method: 'POST' }),
  })
}
