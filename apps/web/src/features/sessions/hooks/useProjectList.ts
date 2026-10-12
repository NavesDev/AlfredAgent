import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../../api/client'
import type { Project } from '../../../api/events'
import { useEvents } from '../../../hooks/useEvents'

const KEY = ['projects'] as const

/** Projects and workspaces, for the new-session form; refetched when one changes. */
export function useProjectList() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: KEY, queryFn: () => api<Project[]>('/api/projects') })
  useEvents((event) => {
    if (event.type.startsWith('project_')) void client.invalidateQueries({ queryKey: KEY })
  })
  return query.data ?? []
}
