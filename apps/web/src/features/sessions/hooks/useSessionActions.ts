import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../../api/client'
import type { SessionView } from '../../../api/events'
import { applySessionEvent } from '../lib/sessions'
import { SESSIONS_KEY } from './useSessions'

const path = (name: string) => `/api/sessions/${encodeURIComponent(name)}`

export function useSessionActions() {
  const client = useQueryClient()
  const update = (event: Parameters<typeof applySessionEvent>[1]) =>
    client.setQueryData<SessionView[]>(SESSIONS_KEY, (list) => applySessionEvent(list ?? [], event))

  const clear = useMutation({
    mutationFn: (name: string) => api<SessionView>(`${path(name)}/clear`, { method: 'POST' }),
    onSuccess: (session) => update({ type: 'session_cleared', session, ts: Date.now() / 1000 }),
  })
  const remove = useMutation({
    mutationFn: (name: string) => api<void>(path(name), { method: 'DELETE' }),
    onSuccess: (_, name) => update({ type: 'session_deleted', name, ts: Date.now() / 1000 }),
  })
  return { clear, remove }
}
