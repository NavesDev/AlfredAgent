import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { api } from '../../../api/client'
import type { UpdateView } from '../../../api/events'
import { useConnection, useEvents } from '../../../hooks/useEvents'

const KEY = ['update'] as const

const post = (path: string) => () => api<UpdateView>(path, { method: 'POST' })

/** The release check (ADR 0013): kept fresh by update_status and refetched on reconnect, which
 * is how the panel notices the restart after an update. */
export function useUpdate() {
  const client = useQueryClient()
  const connection = useConnection()
  const query = useQuery({ queryKey: KEY, queryFn: () => api<UpdateView>('/api/update') })
  useEvents((event) => {
    if (event.type === 'update_status') client.setQueryData(KEY, event.update)
  })
  useEffect(() => {
    if (connection === 'open') void client.invalidateQueries({ queryKey: KEY })
  }, [client, connection])

  const onSuccess = (view: UpdateView) => client.setQueryData(KEY, view)
  const check = useMutation({ mutationFn: post('/api/update/check'), onSuccess })
  const apply = useMutation({ mutationFn: post('/api/update/apply'), onSuccess })
  return { update: query.data, check, apply }
}
