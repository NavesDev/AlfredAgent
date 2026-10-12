import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { api } from '../../../api/client'
import type { SessionView } from '../../../api/events'
import { useConnection, useEvents } from '../../../hooks/useEvents'
import { applySessionEvent } from '../lib/sessions'

export const SESSIONS_KEY = ['sessions'] as const

/** Named sessions: fetched once, then kept current by the session_* events of the /ws. */
export function useSessions() {
  const client = useQueryClient()
  const connection = useConnection()
  const query = useQuery({
    queryKey: SESSIONS_KEY,
    queryFn: () => api<SessionView[]>('/api/sessions'),
    staleTime: Infinity, // the /ws keeps it current; reconnecting refetches below
  })

  useEvents((event) => {
    client.setQueryData<SessionView[]>(SESSIONS_KEY, (list) => applySessionEvent(list ?? [], event))
  })

  // Events published while the socket was down are lost; fetch again after reconnecting.
  useEffect(() => {
    if (connection === 'open') void client.invalidateQueries({ queryKey: SESSIONS_KEY })
  }, [client, connection])

  return query.data ?? []
}
