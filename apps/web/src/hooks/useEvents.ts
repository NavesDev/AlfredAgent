import { useEffect, useRef, useSyncExternalStore } from 'react'
import type { AlfredEvent } from '../api/events'

// One WebSocket for the whole app, reconnecting with backoff. Components subscribe to
// the raw stream; each feature keeps whatever it derives from it in its own hook.

type Listener = (event: AlfredEvent) => void
export type Connection = 'connecting' | 'open' | 'closed'

const listeners = new Set<Listener>()
const statusListeners = new Set<() => void>()
let status: Connection = 'connecting'
let socket: WebSocket | null = null
let retryMs = 500

function setStatus(next: Connection) {
  status = next
  statusListeners.forEach((notify) => notify())
}

function connect() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  socket = new WebSocket(`${proto}://${location.host}/ws`)
  setStatus('connecting')
  socket.onopen = () => {
    retryMs = 500
    setStatus('open')
  }
  socket.onmessage = (message) => {
    const event = JSON.parse(message.data as string) as AlfredEvent
    listeners.forEach((listener) => listener(event))
  }
  socket.onclose = () => {
    setStatus('closed')
    setTimeout(connect, retryMs)
    retryMs = Math.min(retryMs * 2, 3000)
  }
}

/** Feeds fake events into the same stream; used by the demo mode. */
export function emit(event: AlfredEvent) {
  listeners.forEach((listener) => listener(event))
}

export function useEvents(listener: Listener) {
  const latest = useRef(listener)
  useEffect(() => {
    latest.current = listener
  })
  useEffect(() => {
    if (!socket) connect()
    const forward: Listener = (event) => latest.current(event)
    listeners.add(forward)
    return () => {
      listeners.delete(forward)
    }
  }, [])
}

export function useConnection(): Connection {
  return useSyncExternalStore(
    (notify) => {
      statusListeners.add(notify)
      return () => statusListeners.delete(notify)
    },
    () => status,
  )
}
