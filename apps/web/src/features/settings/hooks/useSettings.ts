import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../../api/client'
import type { SettingsView } from '../../../api/events'
import { useEvents } from '../../../hooks/useEvents'

const KEY = ['settings'] as const

export type SettingsUpdate = Partial<Omit<SettingsView, 'known_mcp_servers'>>

export function useSettings() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: KEY, queryFn: () => api<SettingsView>('/api/settings') })
  useEvents((event) => {
    if (event.type === 'settings_updated') client.setQueryData(KEY, event.settings)
  })
  const save = useMutation({
    mutationFn: (body: SettingsUpdate) =>
      api<SettingsView>('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }),
    onSuccess: (settings) => client.setQueryData(KEY, settings),
  })
  return { settings: query.data, save }
}
