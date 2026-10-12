import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import type { UsageView } from '../../../api/events'
import { useConnection, useEvents } from '../../../hooks/useEvents'

const KEY = ['usage'] as const

/** Plan windows, slots and per-session spend; refetched when a report or a session changes. */
export function useUsage() {
  const client = useQueryClient()
  const connection = useConnection()
  const query = useQuery({ queryKey: KEY, queryFn: () => api<UsageView>('/api/usage') })

  useEvents((event) => {
    if (
      event.type === 'rate_limit' ||
      event.type === 'session_status' ||
      event.type === 'settings_updated'
    ) {
      void client.invalidateQueries({ queryKey: KEY })
    }
  })

  useEffect(() => {
    if (connection === 'open') void client.invalidateQueries({ queryKey: KEY })
  }, [client, connection])

  return query.data
}

/** A clock that ticks every half minute, for "reinicia em…" and "lido há…". */
export function useNow(): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 30_000)
    return () => clearInterval(timer)
  }, [])
  return now
}
