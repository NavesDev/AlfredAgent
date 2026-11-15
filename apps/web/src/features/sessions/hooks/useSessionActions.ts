import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../../api/client'
import type { SessionView } from '../../../api/events'
import type { NewSession } from '../../../lib/sessionForm'
import { applySessionEvent } from '../lib/sessions'
import { SESSIONS_KEY } from './useSessions'

const path = (name: string) => `/api/sessions/${encodeURIComponent(name)}`
const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export type SessionChange = { model?: string; effort?: string; description?: string }

export function useSessionActions() {
  const client = useQueryClient()
  const update = (event: Parameters<typeof applySessionEvent>[1]) =>
    client.setQueryData<SessionView[]>(SESSIONS_KEY, (list) => applySessionEvent(list ?? [], event))
  const status = (session: SessionView) =>
    update({ type: 'session_status', session, ts: Date.now() / 1000 })

  const create = useMutation({
    mutationFn: (body: NewSession) => api<SessionView>('/api/sessions', json('POST', body)),
    onSuccess: status,
  })
  const change = useMutation({
    mutationFn: ({ name, ...body }: SessionChange & { name: string }) =>
      api<SessionView>(path(name), json('PATCH', body)),
    onSuccess: status,
  })
  const clear = useMutation({
    mutationFn: (name: string) => api<SessionView>(`${path(name)}/clear`, { method: 'POST' }),
    onSuccess: (session) => update({ type: 'session_cleared', session, ts: Date.now() / 1000 }),
  })
  const remove = useMutation({
    mutationFn: (name: string) => api<void>(path(name), { method: 'DELETE' }),
    onSuccess: (_, name) => update({ type: 'session_deleted', name, ts: Date.now() / 1000 }),
  })
  return { create, change, clear, remove }
}
