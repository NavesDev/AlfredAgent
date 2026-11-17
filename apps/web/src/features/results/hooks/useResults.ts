import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../../api/client'
import type { ResultView } from '../../../api/events'
import { useEvents } from '../../../hooks/useEvents'

/** A session's last results, newest first; refetched when it records a new one. */
export function useResults(session: string) {
  const client = useQueryClient()
  const key = ['results', session]
  const query = useQuery({
    queryKey: key,
    queryFn: () => api<ResultView[]>(`/api/results?session=${encodeURIComponent(session)}`),
  })
  useEvents((event) => {
    if (event.type === 'result_created' && event.result.session === session)
      void client.invalidateQueries({ queryKey: key })
  })
  return query
}

/** One result, for the viewer window. */
export function useResult(id: number) {
  return useQuery({
    queryKey: ['result', id],
    queryFn: () => api<ResultView>(`/api/results/${id}`),
    enabled: Number.isInteger(id) && id > 0,
    retry: false,
  })
}
