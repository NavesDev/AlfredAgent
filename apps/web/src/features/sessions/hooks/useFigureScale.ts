import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../../api/client'
import type { SettingsView } from '../../../api/events'
import { useEvents } from '../../../hooks/useEvents'

const KEY = ['settings'] as const // shared with the settings page's query
const DEFAULT_SCALE = 1.5

/** How many times bigger than their first size the session characters are drawn, from Settings. */
export function useFigureScale(): number {
  const client = useQueryClient()
  const query = useQuery({ queryKey: KEY, queryFn: () => api<SettingsView>('/api/settings') })
  useEvents((event) => {
    if (event.type === 'settings_updated') client.setQueryData(KEY, event.settings)
  })
  return query.data?.figure_scale ?? DEFAULT_SCALE
}
