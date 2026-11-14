import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../../api/client'
import type { Project, SessionView, Workspace } from '../../../api/events'
import type { NewSession } from '../../../lib/sessionForm'
import { useEvents } from '../../../hooks/useEvents'
import { applyProjectEvent } from '../lib/projects'

const KEY = ['projects'] as const
const SESSIONS = ['sessions'] as const
const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

/** Projects with their workspaces, kept current by the project_* events of the /ws. */
export function useProjects() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: KEY, queryFn: () => api<Project[]>('/api/projects') })
  useEvents((event) => {
    client.setQueryData<Project[]>(KEY, (list) => (list ? applyProjectEvent(list, event) : list))
  })
  return { projects: query.data ?? [], loading: query.isPending, error: query.error }
}

/** Sessions, refetched whenever one changes (the dashboard applies events in place instead). */
export function useSessionList() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: SESSIONS, queryFn: () => api<SessionView[]>('/api/sessions') })
  useEvents((event) => {
    if (event.type.startsWith('session_')) void client.invalidateQueries({ queryKey: SESSIONS })
  })
  return query.data ?? []
}

export function useProjectActions() {
  const client = useQueryClient()
  const refresh = () => client.invalidateQueries({ queryKey: KEY })
  const refreshSessions = () => client.invalidateQueries({ queryKey: SESSIONS })
  return {
    create: useMutation({
      mutationFn: (body: { name: string; aliases: string[]; description?: string }) =>
        api<Project>('/api/projects', json('POST', body)),
      onSuccess: refresh,
    }),
    update: useMutation({
      mutationFn: ({
        id,
        ...body
      }: {
        id: number
        name?: string
        aliases?: string[]
        description?: string
      }) => api<Project>(`/api/projects/${id}`, json('PATCH', body)),
      onSuccess: refresh,
    }),
    remove: useMutation({
      mutationFn: (id: number) => api<void>(`/api/projects/${id}`, { method: 'DELETE' }),
      onSuccess: refresh,
    }),
    addWorkspace: useMutation({
      mutationFn: ({
        id,
        ...body
      }: {
        id: number
        name: string
        path: string
        description?: string
      }) => api<Workspace>(`/api/projects/${id}/workspaces`, json('POST', body)),
      onSuccess: refresh,
    }),
    addWorktree: useMutation({
      mutationFn: ({
        id,
        ...body
      }: {
        id: number
        parent_id: number
        name: string
        description?: string
      }) => api<Workspace>(`/api/projects/${id}/worktrees`, json('POST', body)),
      onSuccess: refresh,
    }),
    updateWorkspace: useMutation({
      mutationFn: ({ id, description }: { id: number; description: string }) =>
        api<Workspace>(`/api/workspaces/${id}`, json('PATCH', { description })),
      onSuccess: refresh,
    }),
    removeWorkspace: useMutation({
      mutationFn: ({ id, force }: { id: number; force: boolean }) =>
        api<void>(`/api/workspaces/${id}?force=${force}`, { method: 'DELETE' }),
      onSuccess: refresh,
    }),
    createSession: useMutation({
      mutationFn: (body: NewSession) => api<SessionView>('/api/sessions', json('POST', body)),
      onSuccess: refreshSessions,
    }),
  }
}
